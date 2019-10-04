import os
import tempfile
import shutil
import uuid
from unittest import TestCase, main, mock

from bound import bound


HERE = os.path.abspath(os.path.dirname(__file__))


class TestAggregateDomains(TestCase):
    def test_return_list(self):
        domain_list = bound.aggregate_domains()
        self.assertIsInstance(domain_list, list)

    def test_input_url(self):
        tmpdir = os.path.join(HERE, 'test_data')
        with mock.patch('bound.bound.extract_urls_from_url', return_value=None):
            domains = bound.aggregate_domains(
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
        domains = bound.aggregate_domains(filepath=filepath)
        self.assertIsInstance(domains, list)
        self.assertEqual(3, len(domains))
        self.assertEqual(
            ['ads.google.com', 'dns.google', 'one.one.one.one'],
            domains
        )

    def test_input_combined(self):
        tmpdir = os.path.join(HERE, 'test_data')
        filepath = os.path.join(HERE, 'test_data', 'test_hosts_format_data')
        with mock.patch('bound.bound.extract_urls_from_url', return_value=None):
            domains = bound.aggregate_domains(
                'http://foo.bar.com', filepath=filepath,
                tmpdir=tmpdir, rmtmp=False
            )
        self.assertIsInstance(domains, list)
        self.assertEqual(3, len(domains))
        self.assertEqual(
            ['ads.google.com', 'dns.google', 'one.one.one.one'],
            domains
        )


class TestDownloadFiles(TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir)

    def test_download_files(self):
        bound.download_files([
            'https://en.wikipedia.org/wiki/Main_Page',
            'https://en.wikipedia.org/wiki/2019_Peruvian_constitutional_crisis'
        ], self.tmpdir)
        file_list = os.listdir(self.tmpdir)
        self.assertEqual(len(file_list), 2)
        for listed in file_list:
            try:
                uuid.UUID(listed)
            except Exception:
                self.assertRaises(Exception)


class TestExtractDomain(TestCase):
    def test_extract_domain_comment(self):
        domain = bound.extract_domain('# 0.0.0.0  foo.bar.com')
        self.assertIsNone(domain)
        domain = bound.extract_domain('< abc.com')
        self.assertIsNone(domain)
        domain = bound.extract_domain(':: hello world')
        self.assertIsNone(domain)

    def test_extract_domain_per_line_format(self):
        domain = bound.extract_domain('foo.bar.com')
        self.assertEqual(domain, 'foo.bar.com')

    def test_extract_digit_space_domain_format(self):
        domain = bound.extract_domain('0 foo.bar.com')
        self.assertEqual(domain, 'foo.bar.com')

    def test_extract_domain_line_comment_format(self):
        domain = bound.extract_domain('foo.bar.com  # foo sucks')
        self.assertEqual(domain, 'foo.bar.com')

    def test_extract_domain_hosts_format(self):
        domain = bound.extract_domain('127.0.0.1 foo.bar.com')
        self.assertEqual(domain, 'foo.bar.com')


if __name__ == '__main__':
    main()
