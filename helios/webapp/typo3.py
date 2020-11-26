from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - Typo 3
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Typo3"
        self.types = []

    def detect(self, url):
        directories = ['', 'typo3']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and \
                    ("/typo3" in response.text or 'generator" content="TYPO3' in response.text):
                self.app_url = path
                return True
        return False

    def test(self, url):
        root_page = self.send(url)
        version = None
        if root_page:
            get_version = re.search(r'<meta name="generator" content="typo3 ([\d\.]+)', root_page.text, re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the generator tag" % (self.name, version))
        if not version:
            cl_url = urljoin(url, 'ChangeLog')
            changelog_page = self.send(cl_url)
            version = None
            if changelog_page and changelog_page.url == cl_url:
                get_version = re.search(r'Release of TYPO3 ([\d\.]+)', changelog_page.text, re.IGNORECASE)
                if get_version:
                    version = get_version.group(1)
                    self.logger.info("%s version %s was identified from the ChangeLog file" % (self.name, version))

        if version:
            db = self.get_db("typo3_vulns.json")
            data = json.loads(db)
            vulns = data['Typo3']
            self.match_versions(vulns, version, url)
