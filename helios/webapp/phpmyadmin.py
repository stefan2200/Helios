from helios.webapp import base_app
import re
from helios.core.utils import requests_response_to_dict
import json
import requests
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


# This script detects vulnerabilities in the following PHP based products:
# - phpMyAdmin
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "phpMyAdmin"
        self.types = []

    def detect(self, url):
        directories = ['phpmyadmin', 'pma', 'phpMyAdmin', '']
        for d in directories:
            path = urljoin(url, d)
            response = self.send(path)
            if response and response.status_code == 200 and "phpmyadmin.css.php" in response.text:
                self.app_url = path
                return True
        return False

    def test(self, url):
        docu_url = urljoin(url, "Documentation.html")
        docu_response = self.send(docu_url)
        version = None
        if docu_response:
            get_version = re.search(r'<title>phpMyAdmin\s([\d\.]+)\s', docu_response.text)
            if get_version:
                version = get_version.group(1)
                self.logger.info("phpMyAdmin version %s was identified from the Documentation.html file" % version)

        if version:
            db = self.get_db("phpmyadmin_vulns.json")
            data = json.loads(db)
            pma_vulns = data['phpMyAdmin']
            self.match_versions(pma_vulns, version, url)
        self.test_auth(url)

    def test_auth(self, url):
        sess = requests.session()
        default_creds = ['root:', 'root:admin', 'root:root']
        init_req = sess.get(url)
        if not init_req:
            self.logger.warning("Unable to test authentication, invalid initial response")
            return
        token_re = re.search('name="token".+?value="(.+?)"', init_req.text)

        for entry in default_creds:
            if not token_re:
                self.logger.warning("Unable to test authentication, no token")
                return
            user, passwd = entry.split(':')
            payload = {'lang': 'en', 'pma_username': user, 'pma_password': passwd, 'token': token_re.group(1)}
            post_url = urljoin(url, 'index.php')
            post_response = sess.post(post_url, payload)
            if post_response and 'Refresh' in post_response.headers:
                returl = post_response.headers['Refresh'].split(';')[1].strip()
                retdata = sess.get(returl)
                if retdata:
                    if 'class="loginform">' not in retdata.text:
                        match_str = "Possible positive authentication for user: %s and password %s on %s " % \
                                    (user, passwd, url)
                        result = {
                            'request': requests_response_to_dict(post_response),
                            'match': match_str
                        }
                        self.logger.info(match_str)
                        self.results.append(result)
                        return
                    else:
                        token_re = re.search('name="token".+?value="(.+?)"', retdata.text)






