import re
import requests
from helios.core.utils import aspx_strip_internal, params_from_str
import json
import random
import string
import hashlib
import logging
from bs4 import BeautifulSoup
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

# WIP and very unstable


class Event:
    url = ""
    state_url = ""
    inputs = {}
    actions = []
    session = None
    random_text_size = 8
    user_email = None
    user_password = None

    def __init__(self, session):
        self.session = session
        if not self.session:
            self.session = requests.session()

    def run_actions(self):
        results = []
        for a in self.actions:
            result = self.run_action(a)
            if result:
                results.append([a, result])
        return results

    def run_action(self, action):
        tmp = dict(self.inputs)
        target, argument = action
        internal = aspx_strip_internal(tmp)
        tmp['__EVENTTARGET'] = target
        tmp['__EVENTARGUMENT'] = argument
        print("Submitting action %s:%s" % (target, argument))
        try:
            print("[POST] %s %s" % (self.url, json.dumps(internal)))
            result = self.session.post(self.url, tmp)
            if result:
                print("[%d] %s len:%d type:%s" % (result.status_code, result.url, len(result.text), result.headers['content-type'] if 'content-type' in result.headers else 'Unknown'))
                return result
            return None
        except requests.Timeout:
            print("POST %s resulted in timeout" % self.url)
        except Exception as e:
            print("POST %s caused an exception: %s" % (self.url, str(e)))
        return False

    def generate_random(self, input_type, name):
        name = name.lower()
        # in some cases this allows the crawler to successfully register + login
        if not input_type:
            return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(self.random_text_size))
        if input_type == "email" or "mail" in name:
            if not self.user_email:
                self.user_email = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(self.random_text_size)) + '@' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(self.random_text_size)) + '.com'
            return self.user_email
        if input_type == "password" or "password" in name:
            if not self.user_password:
                self.user_password = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(self.random_text_size))
            return self.user_password

        if input_type in ['number', 'integer', 'decimal']:
            return 1
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(self.random_text_size))


# class with some static methods
class FormDataToolkit:
    def __init__(self):
        pass

    @staticmethod
    def get_checksum(data):
        keys = []
        for x in data:
            keys.append(x)
        return hashlib.md5(''.join(keys).encode('utf-8')).hexdigest()

    @staticmethod
    def get_full_checksum(data):
        keys = []
        for x in data:
            keys.append("{0}={1}".format(x, data[x]))
        return hashlib.md5('&'.join(keys).encode('utf-8')).hexdigest()


class Crawler:
    form_re = re.compile(r'(?s)(<form.+?</form>)', re.IGNORECASE)
    form_action_re = re.compile(r'<form.+?action=[\'"](.*?)[\'"]', re.IGNORECASE)
    hidden_re = re.compile(r'<input(.+?)(?:/)?>', re.IGNORECASE)
    name_re = re.compile(r'name=[\'"](.+?)[\'"]', re.IGNORECASE)
    type_re = re.compile(r'type=[\'"](.+?)[\'"]', re.IGNORECASE)
    value_re = re.compile(r'value=[\'"](.+?)[\'"]', re.IGNORECASE)
    other_types = [
        re.compile(r'(?s)<(select).+?name=[\'"](.+?)[\'"].+?value=[\'"](.*?)[\'"]', re.IGNORECASE),
        re.compile(r'(?s)<(textarea).+?name=[\'"](.+?)[\'"].+?>(.*?)</textarea>', re.IGNORECASE)
    ]
    postback_re = re.compile(r'__doPostBack\(.*?[\'"](.+?)[\'"\\]\s*,\s*[\'"](.*?)[\'"\\]', re.IGNORECASE)
    page_re = [
        re.compile(r'window\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'document\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'document\.location\.href\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'window\.location\.replace\([\'"](.+?)[\'"]'),
        re.compile(r'http-equiv="refresh.+?URL=[\'"](.+?)[\'"]')
    ]
    todo = []
    seen = []
    logger = logging.getLogger("State Crawler")
    max_allowed_checksum = 5

    max_urls = 200
    max_url_unique_keys = 1
    url_variations = []
    ignored = []

    max_postdata_per_url = 10
    max_postdata_unique_keys = 5
    blocked_filetypes = ['.jpg', '.png', '.gif', '.wav', '.mp3', '.mp4', '.3gp', '.js', '.css', 'jpeg', '.pdf', '.ico']
    scope = None

    def __init__(self):
        self.session = requests.session()

    def run(self, url):
        html = self.session.get(url)
        x = self.get_inputs(url, html.text)
        for event in x:
           self.todo.append(event)

        while len(self.todo):
            entry = self.todo.pop(0)
            self.seen.append(entry)
            results = entry.run_actions()
            for result in results:
                result_event, result = result
                x = self.get_inputs(result.url, result.text)
                for event in x:
                    if not self.has_seen_action(event.url, event.inputs):
                        self.todo.append(event)

    def get_filetype(self, url):
        url = url.split('?')[0]
        loc = urlparse.urlparse(url).path.split('.')
        if len(loc) is 1:
            return None
        return ".{0}".format(loc[len(loc)-1].lower())

    def parse_url(self, url, rooturl):
        url = url.split('#')[0]
        url = url.strip()
        if url in self.ignored:
            return
        if self.get_filetype(url) in self.blocked_filetypes:
            self.ignored.append(url)
            self.logger.debug("Url %s will be ignored because file type is not allowed" % url)
            return
        if "?" in url:
            params = params_from_str(url.split('?')[1])
            checksum = FormDataToolkit.get_checksum(params)
            if [url, checksum] in self.url_variations:
                var_num = 0
                for part in self.url_variations:
                    if part == [url, checksum]:
                        var_num += 1
                if var_num >= self.max_url_unique_keys:
                    self.ignored.append(url)
                    self.logger.debug("Url %s will be ignored because key variation limit is exceeded" % url)
                    return
                self.url_variations.append([url, checksum])

        # if local link or link on same site root
        if url.startswith('/') or url.startswith(self.root_url):
            url = urlparse.urljoin(rooturl, url)
            if [url, None] not in self.scraped_pages:
                self.to_crawl.put([url, None])
        # javascript, raw data, mailto etc..
        if not url.startswith('javascript:') or url.startswith('data:') or url.startswith('mailto:'):
            url = urlparse.urljoin(rooturl, url)
            if not self.scope.in_scope(url):
                self.ignored.append(url)
                self.logger.debug("Url %s will be ignored because out of scope" % url)
                return
            if [url, None] not in self.scraped_pages:
                self.to_crawl.put([url, None])

    def parse_links(self, html, rooturl):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                if (len(self.todo) + len(self.seen)) > self.max_urls:
                    continue
                url = link['href']
                self.parse_url(url, rooturl)
            for regex in self.page_re:
                results = regex.findall(html)
                for res in results:
                    self.parse_url(res, rooturl)

        except Exception as e:
            self.logger.warning("Parse error on %s -> %s" % (rooturl, str(e)))

    def has_seen_action(self, url, data):
        for handler in self.seen:
            if handler.url == url:
                checksum = FormDataToolkit.get_checksum(data)
                handler_checksum = FormDataToolkit.get_checksum(handler.inputs)
                if checksum == handler_checksum:
                    return True
        for handler in self.todo:
            if handler.url == url:
                checksum = FormDataToolkit.get_checksum(data)
                handler_checksum = FormDataToolkit.get_checksum(handler.inputs)
                if checksum == handler_checksum:
                    return True
        return False

    def get_inputs(self, url, html):
        data = []
        html = html.replace('&#39;', "'")
        html = html.replace('&amp;', "&")
        for form in self.form_re.findall(html):
            post_url = url
            get_action = self.form_action_re.search(form)
            if get_action:
                post_url = urlparse.urljoin(url, get_action.group(1))
            handler = Event(self.session)
            handler.url = post_url
            handler.state_url = url
            for inp in self.hidden_re.findall(form):
                name = self.name_re.search(inp)
                if not name:
                    continue
                name = name.group(1)
                input_type = self.type_re.search(inp)
                if not input_type:
                    continue
                input_type = input_type.group(1)
                value = self.value_re.search(inp)
                value = value.group(1) if value else handler.generate_random(input_type, name)
                handler.inputs[name] = value
            for match in self.other_types:
                results = match.findall(form)
                for entry in results:
                    handler.inputs[entry[1]] = entry[2]
            for postback in self.postback_re.findall(form):
                if postback not in handler.actions:
                    handler.actions.append(postback)
            data.append(handler)
        return data
