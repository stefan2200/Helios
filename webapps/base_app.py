import requests
import logging
import os


class BaseAPP:
    name = ""
    results = []
    options = {}
    cookies = {}
    logger = None

    def detect(self, url):
        return False

    def run(self, url, scan_options={}):
        self.options = scan_options
        self.logger.debug("Attempting detection of %s on URL: %s" % (self.name, url))
        if self.detect(url):
            self.logger.info("%s was detected on URL: %s" % (self.name, url))
            self.test(url)

    def test(self, url):
        return

    def get_db(self, name):
        db_file = os.path.join(os.path.dirname(__file__), "databases", name)
        if os.path.exists(db_file) and os.path.isfile(db_file):
            with open(db_file, 'r') as f:
                data = f.read()
            return data

    def send(self, url, data=None, headers={}, redirects=True):
        result = None
        cookies = self.cookies
        try:
            if data:
                result = requests.get(url, data=data, headers=headers, cookies=cookies, allow_redirects=redirects, verify=False)
            else:
                result = requests.get(url, headers=headers, cookies=cookies, allow_redirects=redirects, verify=False)
        except Exception as e:
            pass
        return result
