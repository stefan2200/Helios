import requests
import os


class BaseAPP:
    name = ""
    results = []
    options = {}
    cookies = {}
    logger = None
    app_url = None
    scope = None
    headers = {}

    def detect(self, url):
        return False

    def run(self, url, scan_options={}):
        self.options = scan_options
        self.logger.debug("Attempting detection of %s on URL: %s" % (self.name, url))
        if self.detect(url):
            if not self.app_url:
                self.app_url = url
            self.logger.info("%s was detected on URL: %s" % (self.name, self.app_url))
            self.test(self.app_url)

    def test(self, url):
        return

    # function to detect vulnerable versions from CVE entries
    def match_versions(self, vulns, version, url=None):
        for vuln in vulns:
            for vuln_version in vulns[vuln]:
                if version == vuln_version:
                    match_str = "%s version %s appears to be vulnerable to %s (version match: %s)" % \
                                (self.name, version, vuln, vuln_version)
                    result = {
                        'request': {'url': url},
                        'match': match_str
                    }
                    self.logger.info(match_str)
                    self.results.append(result)
                    break
                elif vuln_version.startswith(version):
                    match_str = "%s version %s might be vulnerable to %s (version match: %s)" % \
                                (self.name, version, vuln, vuln_version)
                    result = {
                        'request': {'url': url},
                        'match': match_str
                    }
                    self.logger.info(match_str)
                    self.results.append(result)

    def get_db(self, name):
        db_file = os.path.join(os.path.dirname(__file__), "databases", name)
        if os.path.exists(db_file) and os.path.isfile(db_file):
            with open(db_file, 'r') as f:
                data = f.read()
            return data

    def send(self, url, data=None, headers={}, redirects=True):
        result = None
        cookies = self.cookies
        for k in self.headers:
            headers[k] = self.headers[k]
        try:
            if data:
                result = requests.get(url, data=data, headers=headers, cookies=cookies, allow_redirects=redirects, verify=False)
            else:
                result = requests.get(url, headers=headers, cookies=cookies, allow_redirects=redirects, verify=False)
        except Exception as e:
            self.logger.warning("Request Exception: %s" % str(e))
            pass
        if not self.scope:
            return result
        # check if current URL is still in scope (fixes /blog 302->blog.domain.com issues)
        if result and self.scope.in_scope(result.url):
            return result
        return None
