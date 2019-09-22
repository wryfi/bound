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
    raise SystemExit('Please install the python requests library to use this script.')


logging.basicConfig(level=logging.INFO)

DIGIT_SPACE_DOMAIN_FORMAT = re.compile(r'^\d\s+[\w.-]+$')
DOMAIN_LINE_COMMENT_FORMAT = re.compile(r'^[\w.-]+\s+#.*')
DOMAIN_PER_LINE_FORMAT = re.compile(r'^[\w.-]+$')
HOSTS_FORMAT = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\s+(.*)\s*.*')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-B', '--blacklist-file', help='local blacklist file to parse')
    parser.add_argument('-W', '--whitelist-file', help='local whitelist file to parse')
    parser.add_argument(
        '-b', '--blacklist-url',
        help='URL of blacklist URLs to parse (defaults to the "ticked" list from The Big Blocklist Collection)',
        default='https://v.firebog.net/hosts/lists.php?type=tick'
    )
    parser.add_argument('-i', '--init', help='init system: systemd (default), upstart, or sysv', default='systemd')
    parser.add_argument('-n', '--no-restart', help='do not restart unbound', action='store_true')
    parser.add_argument(
        '-o', '--output',
        help='where to output processed list (/etc/unbound/unbound.conf.d/blacklist.conf)',
        default='/etc/unbound/unbound.conf.d/blacklist.conf'
    )
    parser.add_argument('-w', '--whitelist-url', help='URL of whitelist URLs to parse')
    args = parser.parse_args()

    whitelist = None
    blacklist = None

    blacklist_dir = tempfile.mkdtemp()
    logging.info('blacklist dir: {}'.format(blacklist_dir))
    whitelist_dir = tempfile.mkdtemp()
    logging.info('whitelist_dir: {}'.format(whitelist_dir))

    try:
        if args.whitelist_url:
            get_lists_from_url(args.whitelist_url, whitelist_dir)
            whitelist = parse_lists(whitelist_dir)

        if args.whitelist_file:
            if whitelist:
                whitelist += parse_file(args.whitelist_file)
            else:
                whitelist = parse_file(args.whitelist_file)

        if args.blacklist_url:
            get_lists_from_url(args.blacklist_url, blacklist_dir)
            blacklist = parse_lists(blacklist_dir)

        if args.blacklist_file:
            if blacklist:
                blacklist += parse_file(args.blacklist_file)
            else:
                blacklist = parse_file(args.blacklist_file)

        blacklist = sorted(list(set(blacklist)))

        if whitelist:
            for domain in blacklist:
                if domain in whitelist:
                    blacklist.remove(domain)

        logging.info('blacklisting {} domains'.format(len(blacklist)))

        if os.path.isfile(args.output):
            os.remove(args.output)
        with open(args.output, 'a') as fileobj:
            for blacklisted in blacklist:
                fileobj.write('local-zone: "{}" refuse'.format(blacklisted) + '\n')

        if not args.no_restart:
            restart_unbound(args.init)

    except Exception as ex:
        raise SystemExit('There was an unhandled error running the script: {}'.format(ex))
    finally:
        shutil.rmtree(blacklist_dir)
        shutil.rmtree(whitelist_dir)


def get_lists_from_url(url, output_directory):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        raise SystemExit('Error fetching {}: {}'.format(url, ex))
    for url in response.content.decode().splitlines():
        filename = os.path.join(output_directory, url.split('//')[1].replace('/', '_'))
        try:
            response = requests.get(url)
        except requests.exceptions.HTTPError as ex:
            raise SystemExit('Error fetching {}: {}'.format(url, ex))
        with open(filename, 'w') as file:
            file.write(response.content.decode('latin-1'))


def parse_lists(lists_directory):
    domains = []
    for file in os.listdir(lists_directory):
        file_domains = parse_file(os.path.join(lists_directory, file))
        domains += file_domains
    return domains


def parse_file(filepath):
    domains = []
    with open(filepath, 'r') as fileobj:
        for line in fileobj:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('<') or line.startswith('::'):
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
    logging.info('{} {}'.format(filepath, len(domains)))
    return domains


def restart_unbound(init):
    if init == 'systemd':
        restart = ['systemctl', 'restart', 'unbound']
    elif init == 'upstart':
        restart = ['service', 'unbound', 'restart']
    else:
        restart = ['/etc/init.d/unbound', 'restart']
    if check_config():
        try:
            subprocess.check_call(restart)
        except OSError as ex:
            raise SystemExit('Error calling init: {}. Are you running as root?'.format(ex))
        except subprocess.CalledProcessError as ex:
            raise SystemExit('Error restarting unbound: {}'.format(ex))


def check_config():
    try:
        subprocess.check_call(['unbound-checkconf'])
    except OSError as ex:
        raise SystemExit('Error calling unbound-checkconf: {}. Are you running as root?'.format(ex))
    except subprocess.CalledProcessError:
        raise SystemExit('Something is wrong with unbound configuration!')
    return True


if __name__ == '__main__':
    main()
