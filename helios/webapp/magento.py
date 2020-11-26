from helios.webapp import base_app
import re
import json

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - Magento / Magento2
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Magento"
        self.types = []

    def detect(self, url):
        directories = ['', 'magento', 'shop']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and "Magento" in response.text:
                self.app_url = path
                return True
        return False

    def test(self, url):
        mage_version = urljoin(url, 'magento_version')
        mage_page = self.send(mage_version)
        version = None
        if mage_page:
            # only (accurate) way to get installed version
            get_version = re.search(r'Magento/([\d\.]+)', mage_page.text, re.IGNORECASE)
            if get_version:
                version = get_version.group(1)
                # old versions of Enterprise are actually 2.0
                if version == "1.0" and "Enterprise" in mage_page.text:
                    version = "2.0"
                self.logger.info("%s version %s was identified from the magento_version call" % (self.name, version))

        if version:
            db = self.get_db("magento_vulns.json")
            data = json.loads(db)
            vulns = data['Magento']
            self.match_versions(vulns, version, url)
