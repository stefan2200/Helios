from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - MODX Revolution
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "MODX Revolution"
        self.types = []

    def detect(self, url):
        directories = ['', 'manager']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200:

                if ('<section class="rst-sidemenu' in response.text or
                     '<nav class="rst-topmenu' in response.text):
                    self.app_url = path
                    return True

                if d == "manager" and 'core/modx.js' in response.text:
                    path = urljoin(url, '')
                    self.app_url = path
                    return True
        return False

    def test(self, url):
        # bit of a long shot since there are only limited demo sites available to test on :)
        revo = urljoin(url, 'core/docs/changelog.txt')
        revo_page = self.send(revo)
        version = None
        if revo_page:
            # only (accurate) way to get installed version (ignore the -p1..etc parts since they seem to change a lot)
            get_version = re.search(r'MODX Revolution\s([\d\.]+-\w+)', revo_page.text, re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the core/docs/changelog.txt file" %
                                 (self.name, version))

        if version:
            db = self.get_db("modx_revolution_vulns.json")
            data = json.loads(db)
            vulns = data['Revolution']
            self.match_versions(vulns, version, url)
