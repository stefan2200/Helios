from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - Concrete5
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Concrete5"
        self.types = []

    def detect(self, url):
        directories = ['', 'blog', 'admin']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200:
                if 'concrete5' in response.text:
                    self.app_url = path
                    return True
        return False

    def test(self, url):
        root = urljoin(url, '')
        root_page = self.send(root)
        version = None
        if root_page:
            get_version = re.search(r'<meta name="generator" content="concrete5 - ([\d\.]+)',
                                    root_page.text, re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the generator tag" %
                                 (self.name, version))

        if version:
            db = self.get_db("concrete5_vulns.json")
            data = json.loads(db)
            vulns = data['Concrete5']
            self.match_versions(vulns, version, url)
