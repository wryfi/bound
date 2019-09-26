#!/usr/bin/env python3

import argparse
import logging
import os
import re
import shutil
import subprocess
import tempfile

try:
    import requests
except ImportError:
    raise SystemExit(
        'Please install the python requests library to use this script.'
    )

logging.basicConfig(level=logging.INFO)

DIGIT_SPACE_DOMAIN_FORMAT = re.compile(r'^\d\s+[\w.-]+$')
DOMAIN_LINE_COMMENT_FORMAT = re.compile(r'^[\w.-]+\s+#.*')
DOMAIN_PER_LINE_FORMAT = re.compile(r'^[\w.-]+$')
HOSTS_FORMAT = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+(.*)\s*.*')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-B', '--blocklist-file', help='local blocklist file to parse'
    )
    parser.add_argument(
        '-b', '--blocklist-url',
        help='URL of blocklist URLs to parse (defaults to the "ticked" list from The Big Blocklist Collection)',
        default='https://v.firebog.net/hosts/lists.php?type=tick'
    )
    parser.add_argument(
        '-i', '--init',
        help='init system: systemd (default), upstart, or sysv',
        default='systemd'
    )
    parser.add_argument(
        '-n', '--no-restart', help='do not restart unbound', action='store_true'
    )
    parser.add_argument(
        '-o', '--output',
        help='where to output processed list (/etc/unbound/unbound.conf.d/blocklist.conf)',
        default='/etc/unbound/unbound.conf.d/blocklist.conf'
    )
    parser.add_argument(
        '-S', '--safelist-file', help='local safelist file to parse'
    )
    parser.add_argument(
        '-s', '--safelist-url', help='URL of safelist URLs to parse'
    )
    args = parser.parse_args()

    configure_unbound(
        blocklist_file=args.blocklist_file,
        blocklist_url=args.blocklist_url,
        init=args.init,
        output=args.output,
        restart=not args.no_restart,
        safelist_file=args.safelist_file,
        safelist_url=args.safelist_url
    )


def configure_unbound(
    blocklist_file=None,
    blocklist_url='https://v.firebog.net/hosts/lists.php?type=tick',
    init='systemd',
    output='/etc/unbound/unbound.conf.d/blocklist.conf',
    restart=True,
    safelist_file=None,
    safelist_url=None
):
    safelist = generate_domain_list(safelist_url, safelist_file)
    blocklist = generate_domain_list(blocklist_url, blocklist_file)

    if safelist:
        for domain in blocklist:
            if domain in safelist:
                blocklist.remove(domain)

    logging.info('blocklisting {} domains'.format(len(blocklist)))

    if os.path.isfile(output):
        os.remove(output)
    with open(output, 'a') as fo:
        for blocklisted in blocklist:
            fo.write(
                'local-zone: "{}" refuse'.format(blocklisted) + '\n'
            )

    if restart:
        restart_unbound(init)


def generate_domain_list(url=None, filepath=None, tmpdir=None, rmtmp=True):
    domains = []
    if not tmpdir:
        tmpdir = tempfile.mkdtemp()
    try:
        if url:
            get_lists_from_url(url, tmpdir)
            domains = parse_directory(tmpdir)
        if filepath:
            domains += parse_file(filepath)
    finally:
        if rmtmp:
            shutil.rmtree(tmpdir)
    return sorted(list(set(domains)))


def get_lists_from_url(url, output_directory):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        raise SystemExit('Error fetching {}: {}'.format(url, ex))
    for url in response.content.decode().splitlines():
        filename = os.path.join(
            output_directory, url.split('//')[1].replace('/', '_')
        )
        try:
            response = requests.get(url)
        except requests.exceptions.HTTPError as ex:
            raise SystemExit('Error fetching {}: {}'.format(url, ex))
        with open(filename, 'w') as file:
            file.write(response.content.decode('latin-1'))


def parse_directory(directory):
    domains = []
    logging.debug(directory)
    for file in os.listdir(directory):
        logging.debug(os.path.join(directory, file))
        file_domains = parse_file(os.path.join(directory, file))
        domains += file_domains
    return domains


def parse_file(filepath):
    domains = []
    with open(filepath, 'r') as fileobj:
        for line in fileobj:
            line = line.strip()
            if not line or \
                    line.startswith('#') or \
                    line.startswith('<') or \
                    line.startswith('::'):
                continue
            if re.match(DOMAIN_PER_LINE_FORMAT, line):
                domains.append(line)
            elif re.match(DIGIT_SPACE_DOMAIN_FORMAT, line):
                domains.append(line.split()[1])
            elif re.match(DOMAIN_LINE_COMMENT_FORMAT, line):
                domains.append(line.split()[0])
            else:
                match = re.match(HOSTS_FORMAT, line)
                if match:
                    domain = match.groups()[0]
                    if domain != 'localhost' and domain != 'broadcasthost':
                        domains.append(domain)
    return domains


def restart_unbound(init):
    if init == 'systemd':
        restart = ['systemctl', 'restart', 'unbound']
    elif init == 'upstart':
        restart = ['service', 'unbound', 'restart']
    elif os.path.isfile('/etc/init.d/unbound'):
        restart = ['/etc/init.d/unbound', 'restart']
    else:
        logging.error('No known init system found. Please restart unbound!')
        return
    if check_config():
        try:
            subprocess.check_call(restart)
        except OSError as ex:
            raise SystemExit(
                'Error calling init: {}. Are you running as root?'.format(ex)
            )
        except subprocess.CalledProcessError as ex:
            raise SystemExit('Error restarting unbound: {}'.format(ex))


def check_config():
    try:
        subprocess.check_call(['unbound-checkconf'])
    except OSError as ex:
        raise SystemExit(
            'Error calling unbound-checkconf: {}. Are you running as root?'.format(
                ex
            )
        )
    except subprocess.CalledProcessError:
        raise SystemExit('Something is wrong with unbound configuration!')
    return True


if __name__ == '__main__':
    main()
