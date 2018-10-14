import re
import requests
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import module_base

class Module(module_base.Base):

    def __init__(self):
        self.name = "sitemap.xml"
        self.injections = {}
        self.module_types = ['discovery']
        self.input = "base"
        self.output = "crawler"

    def run(self, base, headers={}, cookies={}):
        self.headers = headers
        self.cookies = cookies
        url = urlparse.urljoin(base, '/robots.txt')
        result = self.send(url, None, None)
        output = []
        if result:
            for entry in re.findall('<loc>(.+?)</loc>', result.text):
                if "*" in entry:
                    # we do not want dem wildcard
                    continue
                newurl = urlparse.urljoin(base, entry).strip()
                newurl = newurl.replace('$', '')
                if newurl == base:
                    continue
                if newurl not in output:
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
            print(e.message)
        return result
