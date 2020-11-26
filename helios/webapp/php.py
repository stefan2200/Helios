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
        self.name = "PHP"
        self.types = []

    def detect(self, url):
        directories = ['']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response:
                if 'Server' in response.headers and 'php' in response.headers['Server'].lower():
                    self.app_url = path
                    return True
                if 'X-Powered-By' in response.headers and 'php' in response.headers['Server'].lower():
                    self.app_url = path
                    return True
                if 'Server' in response.headers and 'apache' in response.headers['Server'].lower() \
                        and 'tomcat' not in response.headers['Server'].lower() \
                        and 'coyote' not in response.headers['Server'].lower():
                    self.app_url = path
                    return True
        return False

    def test(self, url):
        root_page = self.send(url)
        version = None
        if 'Server' in root_page.headers and 'php' in root_page.headers['Server'].lower():

            get_version = re.search(r'php/([\d\.]+)', root_page.headers['Server'], re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                self.logger.info("%s version %s was identified from the Server header tag" % (self.name, version))
        if not version:
            if 'X-Powered-By' in root_page.headers and 'php' in root_page.headers['X-Powered-By'].lower():
                get_version = re.search(r'php/([\d\.]+)', root_page.headers['X-Powered-By'], re.IGNORECASE)
                if get_version:
                    version = get_version.group(1)
                    self.logger.info("%s version %s was identified from the X-Powered-By header tag" %
                                     (self.name, version))

        if version:
            db = self.get_db("php_vulns.json")
            data = json.loads(db)
            vulns = data['PHP']
            self.match_versions(vulns, version, url)
