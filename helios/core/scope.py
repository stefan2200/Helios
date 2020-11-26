try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse
import fnmatch


class Scope:
    host = ""
    scopes = []
    is_https = False
    allow_cross_port = False
    allow_cross_schema = True
    allow_subdomains = False
    _port = 0

    def __init__(self, url, options=None):
        parsed = urlparse(url)
        if url.startswith("https://"):
            self.is_https = True
        self.host = parsed.hostname
        self._port = parsed.port
        if options:
            opts = [x.strip() for x in options.split(',')]
            if "cross_port" in opts:
                self.allow_cross_port = True
            if "no_cross_schema" in opts:
                self.allow_cross_schema = False
            if "allow_subdomains" in opts:
                self.allow_subdomains = True
            if "dont_care" in options:
                self.allow_subdomains = True
                self.allow_cross_port = True

    # Checks if a URL is in scope
    def in_scope(self, url):
        parsed = urlparse(url)
        if not self.allow_cross_port and \
                (parsed.port != self._port or
                 self.allow_cross_schema and parsed.port in [80, 443]):
            return False
        if not self.allow_cross_schema:
            if self.is_https and parsed.scheme != "https":
                return False
            if not self.is_https and parsed.scheme != "http":
                return False
        if parsed.hostname == self.host:
            return True
        for sub_scope in self.scopes:
            if "*" in sub_scope:
                return fnmatch.fnmatch(parsed.netloc, sub_scope)
            if sub_scope == parsed.netloc:
                return True
        if self.allow_subdomains and parsed.netloc.endswith(self.host):
            return True
        return False
