from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - Textpattern
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Textpattern"
        self.types = []

    def detect(self, url):
        directories = ['', 'blog', 'textpattern']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and \
                    ("Textpattern" in response.text or '<body class="front-page"' in response.text):
                self.app_url = path
                return True
        return False

    def test(self, url):
        cl_url = urljoin(url, "README.txt")
        cl_data = self.send(cl_url)
        version = None
        if cl_data:
            get_version = re.search(r'Textpattern CMS ([\d\.]+)', cl_data.text)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the README.txt file" % (self.name, version))

        if version:
            db = self.get_db("textpattern_vulns.json")
            data = json.loads(db)
            subrion_vulns = data['Textpattern']
            self.match_versions(subrion_vulns, version, url)
