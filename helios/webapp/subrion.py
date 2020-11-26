from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - Subrion
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Subrion"
        self.types = []

    def detect(self, url):
        directories = ['', '_core', 'blog', 'subrion']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and \
                    ("Subrion" in response.text or 'jquery.js?fm=' in response.text):
                self.app_url = path
                return True
        return False

    def test(self, url):
        cl_url = urljoin(url, "changelog.txt")
        cl_data = self.send(cl_url)
        version = None
        if cl_data:
            get_version = re.findall(r'From\s[\d\.]+\sto\s([\d\.]+)', cl_data.text)
            if len(get_version):
                version = get_version[-1:][0]
                self.logger.info("%s version %s was identified from the changelog.txt file" % (self.name, version))

        if version:
            db = self.get_db("subrion_vulns.json")
            data = json.loads(db)
            subrion_vulns = data['Subrion']
            self.match_versions(subrion_vulns, version, url)
