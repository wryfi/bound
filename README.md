# bound

The file `bound.py` in this repo is a python script designed to pull
data from [The Big Blocklist Collection](https://firebog.net/) and
generate an [unbound](https://nlnetlabs.nl/projects/unbound/)
configuration file that refuses lookup of the selected domains.

This is useful for blocking ads and malware, in much the same way as
[pi-hole](https://pi-hole.net/). You might prefer this method over
pi-hole if:

* you're already using unbound
* you don't love dnsmasq (which pi-hole is based on)
* you don't think a DNS resolver should require a web server
* you distrust thousands of lines of bash to make major changes to your
system

If the above don't apply to you, or you're looking for an opinionated,
ad-blocking resolver with a pretty user interface and automated
installer, [pi-hole](https://pi-hole.net/) is probably what you want.


## Requirements

1. a gnu/linux or *bsd operating system
1. a working unbound installation
1. python3 (for debian-like systems: `sudo apt-get install python3`)
1. python3 [requests](http://docs.python-requests.org/) library
(for debian-like systems: `sudo apt-get install python3-requests`)


## Installation

Copy `bound.py` to a sensible path on your system, e.g.
`/usr/local/bin`.


## Usage

The script is intended to be used with blacklists from
[The Big Blocklist Collection](https://firebog.net/).

Run without any options, `bound.py` will:

1. download the latest "ticked" list from the Big Blocklist Collection
1. download all of the blacklists listed in the "ticked" list
1. parse, deduplicate, and assemble a list of domains from the retrieved
blacklists
1. remove any whitelisted domains from the list
1. write `/etc/unbound/unbound.conf.d/blacklist.conf` to configure
unbound for blocking the listed domains
1. check the unbound configuration, and exit in case of any errors
1. restart unbound

To accomplish the above, you will probably need to run the script as
the root user.

There are options that support running as a non-root user, as well
as specifying the blacklist URL, an optional whitelist URL, and
local blacklist and whitelist files.

For a description of all the options, run `bound.py -h`.


## Supported File Formats

The `bound.py` script supports blacklists and whitelists in the
following formats:

### one domain per line
```
advanbusiness.com
aoldaily.com
aolon1ine.com
applesoftupdate.com
arrowservice.net
```

### one domain per line, with inline comments
```
quantummetric.com # Cydia/Bigboss
cydia.saurik.com.cdngc.net # Cydia/Bigboss
production-ultimate-assets.ratecity.com.au # NewsCorp
saber.srvcs.tumblr.com # Tumblr
fd-fp3.wg1.b.yahoo.com # Tumblr
```

### hosts file format
```
127.0.0.1  0koryu0.easter.ne.jp
127.0.0.1  109-204-26-16.netconnexion.managedbroadband.co.uk
127.0.0.1  1866809.securefastserver.com
127.0.0.1  2amsports.com
127.0.0.1  4dexports.com
```

### single-digit hosts file format
```
0 1app.blob.core.windows.net
0 2912a.v.fwmrm.net
0 29773.v.fwmrm.net
0 5be16.v.fwmrm.net
0 888casino.com
```