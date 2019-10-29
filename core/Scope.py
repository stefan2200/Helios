try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import fnmatch


class Scope:
    host = ""
    scopes = []
    is_https = False

    def __init__(self, url):
        parsed = urlparse(url)
        if url.startswith("https://"):
            self.is_https = True
        self.host = parsed.hostname

    def in_scope(self, url):
        parsed = urlparse(url)
        if parsed.netloc == self.host:
            return True
        for sub_scope in self.scopes:
            if "*" in sub_scope:
                return fnmatch.fnmatch(parsed.netloc, sub_scope)
            if sub_scope == parsed.netloc:
                return True
        return False
