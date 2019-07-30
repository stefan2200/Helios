import os
import requests
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import modules.module_base


class Module(modules.module_base.Base):

    def __init__(self):
        self.name = "Backup Files"
        self.input = "urls"
        self.injections = {}
        self.module_types = ['discovery']
        self.possibilities = [
            '{url}{extension}~',
            '{url}{extension}.bak',
            '{url}.bak',
            '{url}.backup',
            '{url}.inc',
            '{url}.old',
            '{url}.zip',
            '{url}.txt'
        ]
        self.output = "vulns"

    def run(self, urls, headers={}, cookies={}):
        results = []
        self.cookies = cookies
        self.headers = headers
        list_urls = []
        for u in urls:
            if u[0].split('?')[0] not in list_urls:
                list_urls.append(u[0].split('?')[0])

        for f in list_urls:
            working = 0
            for p in self.possibilities:
                if working > 3:
                    # if something is creating false positives
                    continue
                path = urlparse.urlparse(f).path
                base, ext = os.path.splitext(path)
                u = urlparse.urljoin(f, base)
                p = p.replace('{url}', u)
                p = p.replace('{extension}', ext)
                result = self.send(p, self.headers, self.cookies)
                if result and result.url == p and result.status_code == 200:
                    working += 1
                    results.append(result.url)
        return results

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
           pass
        return result
