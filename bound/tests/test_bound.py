import os
from unittest import TestCase, main, mock

import bound


HERE = os.path.abspath(os.path.dirname(__file__))


class GenerateDomainList(TestCase):
    def test_return_list(self):
        domain_list = bound.generate_domain_list()
        self.assertIsInstance(domain_list, list)

    def test_input_url(self):
        tmpdir = os.path.join(HERE, 'test_data')
        with mock.patch('bound.get_lists_from_url', return_value=None):
            domains = bound.generate_domain_list(
                'http://foo.bar.com', tmpdir=tmpdir, rmtmp=False
            )
        self.assertIsInstance(domains, list)
        self.assertEqual(3, len(domains))
        self.assertEqual(
            ['ads.google.com', 'dns.google', 'one.one.one.one'],
            domains
        )

    def test_input_file(self):
        filepath = os.path.join(HERE, 'test_data', 'test_hosts_format_data')
        domains = bound.generate_domain_list(filepath=filepath)
        self.assertIsInstance(domains, list)
        self.assertEqual(3, len(domains))
        self.assertEqual(
            ['ads.google.com', 'dns.google', 'one.one.one.one'],
            domains
        )

    def test_input_combined(self):
        tmpdir = os.path.join(HERE, 'test_data')
        filepath = os.path.join(HERE, 'test_data', 'test_hosts_format_data')
        with mock.patch('bound.get_lists_from_url', return_value=None):
            domains = bound.generate_domain_list(
                'http://foo.bar.com', filepath=filepath,
                tmpdir=tmpdir, rmtmp=False
            )
        self.assertIsInstance(domains, list)
        self.assertEqual(3, len(domains))
        self.assertEqual(
            ['ads.google.com', 'dns.google', 'one.one.one.one'],
            domains
        )


if __name__ == '__main__':
    main()
