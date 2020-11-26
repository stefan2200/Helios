import re
import requests
try:
    from urllib import quote_plus
    import urlparse
except ImportError:
    from urllib.parse import quote_plus
    import urllib.parse as urlparse
import helios.modules.module_base


class Module(helios.modules.module_base.Base):

    def __init__(self):
        self.name = "Robots.txt"
        self.injections = {}
        self.module_types = ['discovery']
        self.input = "base"
        self.output = "crawler"

    def run(self, url, data=None, headers=None, cookies=None):
        self.headers = headers
        self.cookies = cookies
        url = urlparse.urljoin(url, '/robots.txt')
        result = self.send(url, None, None)
        output = []
        if result:
            for entry in re.findall('(?:[Dd]is)?[Aa]llow:\s*(.+)', result.text):
                if "*" in entry:
                    # we do not want dem wildcard
                    continue
                newurl = urlparse.urljoin(url, entry).strip()
                newurl = newurl.replace('$', '')
                if newurl == url:
                    continue
                if newurl not in output and self.scope.in_scope(newurl):
                    output.append(newurl)
        return output

    def send(self, url, params, data):
        result = None
        headers = self.headers
        cookies = self.cookies
        try:
            if data:
                result = requests.post(url, params=params, data=data, headers=headers, cookies=cookies)
            else:
                result = requests.get(url, params=params, headers=headers, cookies=cookies)
        except Exception as e:
            print(str(e))
        return result
