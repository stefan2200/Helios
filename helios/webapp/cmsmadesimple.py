from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - CMS Made Simple
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "CMS Made Simple"
        self.types = []

    def detect(self, url):
        directories = ['', 'blog']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and \
                    ("cmsmadesimple.org" in response.text or 'index.php?page=' in response.text):
                self.app_url = path
                return True
        return False

    def test(self, url):
        root_page = self.send(url)
        version = None
        if root_page:
            get_version = re.search(r'CMS Made Simple</a> version ([\d\.]+)', root_page.text, re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the footer tag" % (self.name, version))

        if version:
            db = self.get_db("cmsmadesimple_vulns.json")
            data = json.loads(db)
            vulns = data['CmsMadeSimple']
            self.match_versions(vulns, version, url)
