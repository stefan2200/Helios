from base64 import b64encode
import re
import sys
import logging
import requests
try:
    from urllib import parse
except ImportError:
    import urlparse as parse


class LoginAction:
    session_obj = None
    headers = {}
    cookies = {}
    logger = None

    def __init__(self, logger=logging.INFO):
        self.session_obj = requests.session()
        self.logger = logging.getLogger("Login")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def basic_auth(self, up_str):
        value = b64encode(up_str.encode()).decode()
        header = "Basic %s" % value
        self.logger.info("Using header Authorization: %s" % header)
        self.headers['Authorization'] = header

    def login_form(self, url, data, headers={}):
        try:
            data = dict(parse.parse_qsl(data))
        except Exception as e:
            self.logger.error("Login Error: login payload should be in urlencoded format: %s" % str(e))
            return None

        for k in headers:
            self.headers[k] = headers[k]
        self.session_obj.get(url)
        self.logger.debug("Login payload: %s" % str(data))
        return self.session_obj.post(url, data=data, headers=self.headers, allow_redirects=False)

    def login_form_csrf(self, url, data, headers={}, token_url=None):
        try:
            data = dict(parse.parse_qsl(data))
        except Exception as e:
            self.logger.error("Login Error: login payload should be in urlencoded format: %s" % str(e))
            return None
        if not token_url:
            token_url = url

        for k in headers:
            self.headers[k] = headers[k]

        page = self.session_obj.get(token_url)
        page_data = {}
        for x in re.findall('(<input.+?>)', page.text, re.IGNORECASE):
            n = re.search('name="(.+?)"', x, re.IGNORECASE)
            v = re.search('value="(.+?)"', x, re.IGNORECASE)
            if n and v:
                page_data[n.group(1)] = v.group(1)

        for custom in data:
            page_data[custom] = data[custom]
        self.logger.debug("Login payload: %s" % str(page_data))
        return self.session_obj.post(url, data=page_data, headers=self.headers, allow_redirects=False)

    def pre_parse(self, options):
        headers = options.login_header
        if not options.login_type:
            return None
        self.logger.info("Running Login Sequence")
        if headers:
            try:
                for header in headers:
                    s = header.split(':')
                    key = s[0].strip()
                    value = ':'.join(s[1:])
                    self.headers[key] = value
            except Exception as e:
                self.logger.warning("Login Error: Error processing headers: %s" % str(e))

        if options.login_type == "basic":
            creds = options.login_creds
            if not creds:
                self.logger.error("Login Error: --login-creds is required for Basic Auth")
                return None
            self.basic_auth(creds)

        if options.login_type == "header":
            if not headers:
                self.logger.error("Login Error: at least one --login-header is required for Header Auth")
                return None

        token_url = options.token_url
        url = options.login_url
        data = options.login_data
        if not token_url:
            token_url = url
        try:
            if options.login_type == "form":
                return self.login_form(url=token_url, data=data)
            if options.login_type == "form-csrf":
                return self.login_form_csrf(url=url, data=data, token_url=token_url)
        except Exception as e:
            self.logger.error("Error in Login sequence: %s" % str(e))
