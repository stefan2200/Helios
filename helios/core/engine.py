import re
import fnmatch
from helios.core.utils import *
from helios.core.request import *
import copy
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse


class Engine:
    script = {}


class CookieLib:
    cookiefile = None
    cookies = {

    }
    parsed = {}
    domain = None

    def __init__(self, cookiefile=None):
        self.cookiefile = cookiefile

    def set(self, string):
        string = string.replace('; ', ';')
        parts = string.split(';')
        p = parts[0]
        p = p.strip()
        cookie_key, cookie_value = p.split('=')
        secure = "Secure" in parts
        httponly = "HttpOnly" in parts
        self.parsed[cookie_key] = {
            "value": cookie_value,
            "is_secure": secure,
            "is_httponly": httponly
        }
        # if not cookie_key in self.cookies:
        #    print("[COOKIELIB] Cookie %s=%s was set" % (cookie_key, cookie_value))

        self.cookies[cookie_key] = cookie_value

    def append(self, cookieset):
        for key in cookieset:
            self.parsed[key] = {"value": cookieset[key], "is_secure": False, "is_httponly": True}
            self.cookies[key] = cookieset[key]

    def get(self):
        outstr = ""
        if len(self.cookies) == 0:
            return None
        for c in self.cookies:
            outstr += "%s=%s; " % (c, self.cookies[c]["value"])
        return outstr[:-2]

    def autoparse(self, headers):
        plain = multi_to_lower(headers)
        if 'set-cookie' in plain:
            self.set(plain['set-cookie'])


class MatchObject:
    is_ok = True
    match_type = ""
    match = ""
    match_location = ""  # body, headers, cookie
    options = []
    name = "Template, please set name"

    def __init__(self, mtype, match, location, name, options=[]):
        self.match_type = mtype
        self.match_location = location
        self.match = match
        self.options = options
        self.name = name
        self.test_regex()

    def test_regex(self):
        if self.match_type == "regex":
            try:
                re.compile(self.match)
            except Exception as e:
                print("Compilation of regex %s has failed, disabling script" % self.match)
                print("Error: %s" % str(e))
                self.is_ok = False

    def run(self, response_object):
        if not response_object:
            return False
        if self.match_location == "status_code":
            if self.match_type == "contains":
                if self.match in str(response_object.code):
                    return "(%s) status code: %s was found" % (self.name, self.match)
            if self.match_type == "equals":
                try:
                    if response_object.code == int(self.match):
                        return "(%s) status code: %s was found" % (self.name, self.match)
                except:
                    pass

        if self.match_location == "body":
            search = response_object.text
            if "ignore_case" in self.options:
                search = search.lower()

            if "ascii" in self.options:
                search = search.encode('ascii', 'ignore')

            if "utf-8" in self.options:
                search = search.encode('utf-8', 'ignore')

            if self.match_type == "contains":
                if self.match in search:
                    return "Match: %s was found" % self.match

            if self.match_type == "regex":
                r = re.compile(self.match)
                regresult = r.search(search) if "multi_line" not in self.options else r.search(search, re.MULTILINE)
                if regresult:
                    matches = ', '.join(regresult.groups()) if len(regresult.groups()) > 0 else None
                    if 'strip_newlines' in self.options and matches:
                        matches = matches.replace("\n", "")
                    return "Regex Match: %s was found %s" % (self.match, "match : %s" % matches if matches else '')

            if self.match_type == "fnmatch":
                if fnmatch.fnmatch(search, self.match):
                    return "fnmatch: %s was found" % self.match

        if self.match_location == "headers":
            headers = response_object.headers
            if "ignore_case" in self.options:
                headers = multi_to_lower(headers, also_values="ignore_case_values" in self.options)

            if self.match_type == "exists":
                if self.match in headers:
                    return "Header %s: %s exists" % (self.match, headers[self.match])

            if self.match_type.startswith('contains:'):
                key = self.match_type.replace('contains:', '')
                if key in headers:
                    if self.match in headers[key]:
                        return "Header %s: %s matches %s" % (key, headers[key], self.match)

            if self.match_type.startswith("regex:"):
                key = self.match_type.replace('regex:', '')
                if key in headers:
                    r = re.compile(self.match)
                    if r.search(headers[key]):
                        return "Regex Match: %s was found on header %s: %s" % (self.match, key, headers[key])
            return False


class CustomRequestBuilder:
    root_url = ""
    match = None
    url = ""
    data = None
    headers = {}
    options = []

    def __init__(self, url, data, headers={}, options=[]):
        self.url = url
        self.data = data
        self.headers = headers

    def run(self):
        newurl = ""
        if "rootdir" in self.options:
            data = urlparse(self.root_url)
            result = '{uri.scheme}://{uri.netloc}/'.format(uri=data)
            newurl = urljoin(result, self.url)
        else:
            newurl = urljoin(self.root_url, self.url)
        request = Request(
            url=newurl,
            data=self.data,
            headers=self.headers
        )
        request.run()
        if request.is_ok and request.is_done:
            return request
        return False


class RequestBuilder:
    initial_request = None
    itype = None
    value = None
    debug = False
    results = []
    name = ""

    def __init__(self, req, inject_type, inject_value, matchobject, name):
        self.initial_request = copy.copy(req)
        self.itype = inject_type
        self.value = inject_value
        self.m = matchobject
        self.value = self.value.replace('{null}', '\0')
        self.value = self.value.replace('{crlf}', '\r\n')
        self.name = name

    def execute(self, new_request):
        new_request.run()
        if new_request.is_done and new_request.is_ok:
            return new_request.response
        return None

    def test(self, response):
        if self.debug:
            print(response.to_string())
        for match in self.m:
            result = match.run(response)
            if result:
                return result
        return None

    def found(self, response, match):
        mobj = {"request": response_to_dict(response), "match": match}
        if mobj not in self.results:
            self.results.append(mobj)

    def run_on_parameters(self):
        original_url = self.initial_request.url
        if "?" in self.initial_request.url:
            url, parameters = self.initial_request.url.split('?')
            params = params_from_str(parameters)
            tmp = {}
            for p in params:
                tmp = dict(params)
                tmp[p] = self.value.replace('{value}', params[p])
                request = self.initial_request
                request.url = "%s?%s" % (url, params_to_str(tmp))
                response = self.execute(request)
                result = None
                result = self.test(response)
                if result:
                    self.found(response, result)
        if self.initial_request.data:
            data = self.initial_request.data
            if type(data) == str:
                data = params_from_str(data)
            tmp = {}
            for p in data:
                tmp = dict(data)
                if not data[p]:
                    data[p] = ""
                tmp[p] = self.value.replace('{value}', data[p])
                request = self.initial_request
                request.url = original_url
                request.data = tmp
                response = self.execute(request)
                result = self.test(response)
                if result:
                    self.found(response, result)

    def run(self):
        self.results = []
        if "parameters" in self.itype:
            self.run_on_parameters()
        return self.results
