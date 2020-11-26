import requests
from helios.core import response


class Request:
    url = ""
    data = None
    headers = None
    cookies = None
    redirect = False
    is_done = False
    is_ok = False
    response = None
    request_headers = {}

    def __init__(self, url, data=None, headers=None, cookies=None, redir=True, agent=None):
        self.url = url
        self.data = data
        self.headers = headers
        if agent:
            if not self.headers:
                self.headers = {}
            self.headers['User-Agent'] = agent
        self.cookies = cookies
        self.redirect = redir

    def run(self):
        result = None
        if self.data:
            try:
                result = requests.post(self.url,
                                       data=self.data,
                                       headers=self.headers,
                                       cookies=self.cookies,
                                       allow_redirects=self.redirect,
                                       verify=False)
            except:
                result = -1
        else:
            try:
                result = requests.get(self.url,
                                      headers=self.headers,
                                      cookies=self.cookies,
                                      allow_redirects=self.redirect,
                                      verify=False)
            except:
                result = -1
        if result == -1:
            self.is_done = True
            self.is_ok = False
            return
        self.request_headers = result.request.headers
        self.is_done = True
        if result:
            r = response.Raw(
                text=result.text,
                code=result.status_code,
                cookies=result.cookies,
                headers=result.headers,
                final_url=result.url,
                ctype=result.headers.get('content-type'),
                object=self
            )
            self.response = r
            self.is_ok = True

