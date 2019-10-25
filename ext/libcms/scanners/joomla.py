import sys
import os
# extend the path with the current file, allows the use of other CMS scripts
sys.path.insert(0, os.path.dirname(__file__))
import cms_scanner
import re
import json
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse


class Scanner(cms_scanner.Scanner):
    def __init__(self):
        self.name = "joomla"
        self.update_frequency = 3600 * 48

    def get_version(self, url):
        text = self.get(urljoin(url, "language/en-GB/en-GB.xml"))
        if text:
            version_check_1 = re.search('<version>(.+?)</version>', text.text)
            if version_check_1:
                self.logger.info(
                    "Detected %s version %s on %s trough language file" % (self.name, version_check_1.group(1), url))
                return version_check_1.group(1)
        text = self.get(urljoin(url, "administrator/manifests/files/joomla.xml"))
        if text:
            version_check_2 = re.search('<version>(.+?)</version>', text.text)
            if version_check_2:
                self.logger.info(
                    "Detected %s version %s on %s trough admin xml" % (self.name, version_check_2.group(1), url))
                return version_check_2.group(1)
        text = self.get(urljoin(url, 'plugins/editors/tinymce/tinymce.xml'))
        if text:
            version_check_3 = re.search('<version>(.+?)</version>', text.text)
            if version_check_3:
                sub = version_check_2.group(1)
                # removed lowest versions to prevent false positives
                sub_versions = {
                    '3.5.6': '3.1.6',
                    '4.0.10': '3.2.1',
                    '4.0.12': '3.2.2',
                    '4.0.18': '3.2.4',
                    '4.0.22': '3.3.0',
                    '4.0.28': '3.3.6',
                    '4.1.7': '3.4.0',
                }
                self.logger.info("Could not determine version but TinyMCE is present, " +
                                 "detection will probably not be very accurate")
                if sub in sub_versions:
                    return sub_versions[sub]
        self.logger.warning("Unable to determine CMS version on url %s" % url)
        return None

    def run(self, base):
        self.set_logger()
        self.setup()

        version = self.get_version(base)
        self.logger.info("Because Joomla compononents are too wide-spread"
                         " the default scanner should detect most vulnerabilities")
        return {
            'version': version,
            'plugins': [],
            'plugin_vulns': [],
            'version_vulns': [],
            'discovery': []
        }



