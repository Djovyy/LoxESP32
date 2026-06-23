#!/usr/bin/perl
use strict;
use warnings;
use LoxBerry::Web;
use LoxBerry::Log; # Modulul nativ pentru loguri
use JSON;
use LWP::UserAgent;
use HTTP::Request::Common qw(POST);
use CGI qw(:standard);

# ---------- CONFIG ----------
my $data_file = "$lbpdatadir/devices.json";
my $title = "LoxESP32 OTA Manager";
# ----------------------------

# Inițializăm obiectul de logare nativ LoxBerry
my $log = LoxBerry::Log->new(
    package => 'LoxESP32',
    name => 'OTA_Manager',
    filename => "$lbplogdir/loxesp32.log",
    append => 1
);

# Creăm fișierul JSON dacă nu există
if (!-d "$lbpdatadir") {
    mkdir("$lbpdatadir", 0755);
}
if (!-e $data_file) {
    open my $fh, ">", $data_file;
    print $fh "[]";
    close $fh;
}

# Funcții pentru a încărca/salva lista de dispozitive
sub load_devices {
    open my $fh, "<", $data_file or return [];
    my $json = do { local $/; <$fh> };
    close $fh;
    my $arr = eval { decode_json($json) } || [];
    return $arr;
}

sub save_devices {
    my ($arr) = @_;
    open my $fh, ">", $data_file or return;
	use Scalar::Util 'blessed';

	for my $item (@$arr) {
        for my $k (keys %$item) {
            if (blessed($item->{$k})) {
                $item->{$k} = "$item->{$k}";
            }
        }
    }
    print $fh encode_json($arr);
    close $fh;
}

# Inițializăm variabilele
my $msg = "";
my $action = param('action') // '';
my $ua = LWP::UserAgent->new(timeout => 10);

# Executăm acțiunile POST
if ($ENV{'REQUEST_METHOD'} eq 'POST' && $action ne '') {
    my $devices = load_devices();

    if ($action eq 'add') {
        my $name = trim(param('name') // '');
        my $ip   = trim(param('ip') // '');
        if ($name ne '' && $ip ne '') {
            push @$devices, {
                name      => $name,
                ip        => $ip,
                status    => 'unknown',
                last_ping => ''
            };
            save_devices($devices);
            $msg = "Device added.";
        } else {
            $msg = "Name and IP required.";
        }

    } elsif ($action eq 'update_save') {
        my $old_ip = trim(param('old_ip') // '');
        my $name   = trim(param('name') // '');
        my $ip     = trim(param('ip') // '');
        
        if ($name ne '' && $ip ne '') {
            foreach my $d (@$devices) {
                if ($d->{ip} eq $old_ip) {
                    $d->{name} = $name;
                    $d->{ip}   = $ip;
                }
            }
            save_devices($devices);
            $msg = "Device updated.";
        } else {
            $msg = "Name and IP required.";
        }

    } elsif ($action eq 'delete') {
        my $ip = param('ip') // '';
        my @filtered = grep { $_->{ip} ne $ip } @$devices;
        save_devices(\@filtered);
        $msg = "Device removed.";

        } elsif ($action eq 'ping') {
        # Pornim logarea acțiunii de Ping (Sintaxa corectă globală)
        LOGSTART("Manual ping initiated");
        
        my $ip = param('ip') // '';
        my $url = "http://$ip/status";
        my $res = $ua->get($url);
        
        foreach my $d (@$devices) {
            if ($d->{ip} eq $ip) {
                $d->{last_ping} = scalar localtime();
                $d->{status} = $res->is_success ? 'online' : 'offline';
            }
        }
        save_devices($devices);
        
        if ($res->is_success) {
            $msg = "Ping result: HTTP 200 OK";
            LOGOK("Device at IP $ip is ONLINE.");
        } else {
            $msg = "Ping result: offline";
            LOGWARN("Device at IP $ip is OFFLINE. Error: " . $res->status_line); # Acum funcționează LOGWARN!
        }
        
        LOGEND("Ping finished");

     } elsif ($action eq 'ota') {
        # Pornim logarea acțiunii de OTA Update
        LOGSTART("OTA Firmware Update initiated");
        
        my $ip = param('ip') // '';
        my $filename = param('firmware') // '';
        if ($filename eq '') {
            $msg = "Firmware upload missing.";
            LOGERR("OTA failed: No file selected for upload.");
        } else {
            my $upload_fh = upload('firmware');
            my $tmpfile = "/tmp/" . $filename;
            open(my $out, '>', $tmpfile);
            binmode $out;
            while (<$upload_fh>) { print $out $_; }
            close $out;

            my $url = "http://$ip/update";
            LOGINF("Sending firmware file to $url...");
            
            my $req = POST($url, Content_Type => 'form-data', Content => [ update => [$tmpfile] ]);
            my $res = $ua->request($req);

            if ($res->is_success) {
                $msg = "OTA successful.";
                LOGOK("OTA Update successfully completed for device IP: $ip");
            } else {
                $msg = "OTA failed. Check logs.";
                LOGERR("OTA Update FAILED for IP $ip. Reason: " . $res->status_line);
            }

            unlink $tmpfile if -e $tmpfile;
        }
        
        LOGEND("OTA action finished");
    }
}

# Încarcă dispozitivele actuale
my $devices = load_devices();

# Pregătim structura pentru template
my $template = HTML::Template->new(
    filename => "$lbptemplatedir/index.html",
    global_vars => 1
);

$template->param(MSG => $msg);

# Logica de completare pentru Editare
my $edit_ip = param('edit_ip') // '';
if ($edit_ip ne '') {
    foreach my $d (@$devices) {
        if ($d->{ip} eq $edit_ip) {
            $template->param(IS_EDIT   => 1);
            $template->param(EDIT_NAME => $d->{name});
            $template->param(EDIT_IP   => $d->{ip});
        }
    }
}

if (@$devices) {
    $template->param(DEVICES_EXIST => 1);
    my @loop;
    foreach my $d (@$devices) {
        push @loop, {
            NAME      => $d->{name},
            IP        => $d->{ip},
            STATUS    => $d->{status},
            LAST_PING => $d->{last_ping},
        };
    }
    $template->param(DEVICES => \@loop);
}

# GENERARE COMODĂ DE BUTON PENTRU LOGURI (NATIV LOXBERRY)
# Această linie va citi fișierele de log și va genera tabelul grafic pentru interfață
my $loglist = LoxBerry::Web::loglist_html();
$template->param(LOGLIST_HTML => $loglist);

# Afișăm în interfața LoxBerry
LoxBerry::Web::lbheader($title);
print $template->output();
LoxBerry::Web::lbfooter();

# ---------- FUNCȚII UTILE ----------
sub trim {
    my $s = shift // "";
    $s =~ s/^\s+|\s+$//g;
    return $s;
}
