import argparse
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid

try:
    import requests
except ImportError:
    raise SystemExit(
        'Please install the python requests library to use this application.'
    )


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(
    logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s :: %(message)s')
)
logger.addHandler(console)


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
    safelist = aggregate_domains(safelist_url, safelist_file)
    blocklist = aggregate_domains(blocklist_url, blocklist_file)

    if safelist:
        for domain in blocklist:
            if domain in safelist:
                blocklist.remove(domain)

    logger.info(f'blocklisting {len(blocklist)} domains')

    if os.path.isfile(output):
        os.remove(output)
    with open(output, 'a') as fo:
        for blocklisted in blocklist:
            fo.write(
                f'local-zone: "{blocklisted}" refuse' + '\n'
            )

    if restart:
        restart_unbound(init)


def aggregate_domains(url=None, filepath=None, tmpdir=None, rmtmp=True):
    domains = []
    tmpdir = tmpdir if tmpdir else tempfile.mkdtemp()
    try:
        if url:
            assemble_lists_from_url(url, tmpdir)
            domains = parse_directory(tmpdir)
        if filepath:
            domains += parse_file(filepath)
    finally:
        if rmtmp:
            shutil.rmtree(tmpdir)
    return sorted(list(set(domains)))


def assemble_lists_from_url(url, output_directory):
    url_list = extract_urls_from_url(url)
    download_files(url_list, output_directory)


def extract_urls_from_url(source_url):
    try:
        response = requests.get(source_url)
        response.raise_for_status()
    except requests.exceptions.HTTPError as ex:
        raise SystemExit(f'Error fetching {source_url}: {ex}')
    return response.content.decode().splitlines()


def download_files(urls, output_directory):
    urls = urls if urls else []
    for url in urls:
        try:
            response = requests.get(url)
        except Exception as ex:
            logger.warning(f'Failed to fetch url: {ex}')
            continue
        filename = os.path.join(
            output_directory, str(uuid.uuid4())
        )
        with open(filename, 'w') as file:
            file.write(response.content.decode('latin-1'))


def parse_directory(directory):
    domains = []
    for file in os.listdir(directory):
        file_domains = parse_file(os.path.join(directory, file))
        domains += file_domains
    return domains


def parse_file(filepath):
    domains = []
    with open(filepath, 'r') as fileobj:
        for line in fileobj:
            line = line.strip()
            domain = extract_domain(line)
            if domain:
                domains.append(domain)
    return domains


def extract_domain(line):
    if not line or re.match(r'^(?:#|<|::).*', line):
        return
    if re.match(DOMAIN_PER_LINE_FORMAT, line):
        return line
    elif re.match(DIGIT_SPACE_DOMAIN_FORMAT, line):
        return line.split()[1]
    elif re.match(DOMAIN_LINE_COMMENT_FORMAT, line):
        return line.split()[0]
    else:
        match = re.match(HOSTS_FORMAT, line)
        if match:
            domain = match.groups()[0]
            if domain != 'localhost' and domain != 'broadcasthost':
                return domain


def restart_unbound(init):
    if init == 'systemd':
        restart = ['systemctl', 'restart', 'unbound']
    elif init == 'upstart':
        restart = ['service', 'unbound', 'restart']
    elif os.path.isfile('/etc/init.d/unbound'):
        restart = ['/etc/init.d/unbound', 'restart']
    else:
        logger.error('No known init system found. Please restart unbound!')
        return
    if check_config():
        try:
            subprocess.check_call(restart)
        except OSError as ex:
            raise SystemExit(
                f'Error calling init: {ex}. Are you running as root?'
            )
        except subprocess.CalledProcessError as ex:
            raise SystemExit(f'Error restarting unbound: {ex}')


def check_config():
    try:
        subprocess.check_call(['unbound-checkconf'])
    except OSError as ex:
        raise SystemExit(
            f'Error calling unbound-checkconf: {ex}. Are you running as root?'
        )
    except subprocess.CalledProcessError:
        raise SystemExit('Something is wrong with unbound configuration!')
    return True


if __name__ == '__main__':
    main()
