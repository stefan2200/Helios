try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class Scope:
    host = ""
    is_https = False

    def __init__(self, url):
        parsed = urlparse(url)
        if url.startswith("https://"):
            self.is_https = True
        self.host = parsed.hostname

    def in_scope(self, url):
        parsed = urlparse(url)
        return parsed.hostname == self.host