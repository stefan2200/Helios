import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from core.Utils import params_from_str
import time
import json
import random
import re
import string
import hashlib
import os
from core.Engine import CookieLib
import sys

try:
    import urlparse
    from Queue import Queue, Empty
except ImportError:
    import urllib.parse as urlparse
    from queue import Queue, Empty


# Main Crawler module, uses BeautifulSoup4 to extract url / form data

class Crawler:
    # checksum, array of possible values
    postdata = []
    max_allowed_checksum = 5

    max_urls = 200
    max_url_unique_keys = 5
    url_variations = []
    ignored = []

    max_postdata_per_url = 10
    max_postdata_unique_keys = 5
    blocked_filetypes = ['.jpg', '.png', '.gif', '.wav', '.mp3', '.mp4', '.3gp', '.js', '.css', 'jpeg', '.pdf', '.ico']
    output_filename = "tmp.json"
    thread_count = 5
    cookie = CookieLib()
    is_debug = True
    logger = None
    headers = {}
    data_dir = "data"
    page_re = [
        re.compile('window\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile('document\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile('document\.location\.href\s*=\s*[\'"](.+?)[\'"]'),
        re.compile('window\.location\.replace\([\'"](.+?)[\'"]'),
        re.compile('http-equiv="refresh.+?URL=[\'"](.+?)[\'"]')
    ]
    write_output = True
    scope = None
    base_url = None

    def __init__(self, base_url, agent=None, logger=logging.INFO, scope=None):
        self.base_url = base_url
        self.root_url = '{}://{}'.format(urlparse.urlparse(self.base_url).scheme, urlparse.urlparse(self.base_url).netloc)
        self.pool = ThreadPoolExecutor(max_workers=self.thread_count)
        self.scraped_pages = []
        self.to_crawl = Queue()
        self.to_crawl.put([self.base_url, None])
        self.output_filename = os.path.join(self.data_dir, 'crawler_%s_%d.json' % (urlparse.urlparse(self.base_url).netloc, time.time()))
        self.logger = logging.getLogger("Crawler")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.debug("Starting Crawler")
        if agent:
            self.headers['User-Agent'] = agent
            self.logger.debug("Using User-Agent %s for crawling" % agent)
        if not os.path.exists(self.data_dir):
            self.logger.info("Data directory %s does not exist, creating" % self.data_dir)
            os.mkdir(self.data_dir)
        self.scope = scope

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
                if (self.to_crawl.qsize() + len(self.scraped_pages)) > self.max_urls:
                    continue
                url = link['href']
                self.parse_url(url, rooturl)
            for regex in self.page_re:
                results = regex.findall(html)
                for res in results:
                    self.parse_url(res, rooturl)

        except Exception as e:
            self.logger.warning("Parse error on %s -> %s" % (rooturl, str(e)))

    def get_col(self, arr, col):
        return map(lambda x: x[col], arr)

    def scrape_info(self, html, rooturl):
        e = Extractor(html, rooturl)
        forms = e.extract(fill_empty=True)
        for f in forms:
            url, data = f
            checksum = FormDataToolkit.get_checksum(data)
            if checksum not in self.get_col(self.postdata, 0):
                if [url, data] not in self.scraped_pages:
                    if not self.scope.in_scope(url):
                        self.ignored.append(url)
                        self.logger.debug("Url %s will be ignored because out of scope" % url)
                        continue
                    self.to_crawl.put([url, data])
                self.postdata.append([checksum, url, data])

    def post_scrape_callback(self, res):
        result = res.result()
        if result and result.status_code == 200:
            self.parse_links(result.text, result.url)
            self.scrape_info(result.text, result.url)
            try:
                self.cookie.autoparse(result.headers)
            except Exception as e:
                print(str(e))

    def scrape_page(self, url):
        url, data = url
        try:
            res = requests.get(url, timeout=(3, 30), cookies=self.cookie.cookies, allow_redirects=False, headers=self.headers, verify=False) if not data else requests.post(url, data, cookies=self.cookie.cookies, allow_redirects=False, timeout=(3, 30), verify=False)
            return res
        except requests.RequestException:
            return
        except Exception as e:
            self.logger.warning("Error in thread: %s" % str(e))
            return

    def has_page(self, url, data):
        for u, d in self.scraped_pages:
            if url == u and data == d:
                return True
        return False

    def run_scraper(self):
        emptyrun = 0
        while True:
            try:
                target_url = self.to_crawl.get(timeout=10)
                if not self.has_page(target_url[0], target_url[1]):
                    self.logger.info("Scraping URL: {}".format(target_url))
                    self.scraped_pages.append([target_url[0], target_url[1]])
                    job = self.pool.submit(self.scrape_page, target_url)
                    job.add_done_callback(self.post_scrape_callback)
                    emptyrun += 1
            except Empty:
                break
            except Exception as e:
                self.logger.warning("Error: %s" % str(e))
                continue
            self.logger.debug("Todo: {0} Done: {1}".format(self.to_crawl.qsize(), len(self.scraped_pages)))
        if self.write_output:
            output = json.dumps(self.scraped_pages)
            with open(self.output_filename, 'w') as f:
                f.write(output)


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


# the Extractor class is used to extract forms from HTML
# the default extract() method is equipped with the functionality to automatically fill in input fields
# dunno if textarea works :)
class Extractor:
    body = None
    url = None
    random_text_size = 8
    user_email = None
    user_password = None

    def __init__(self, text, original_url = ""):
        soup = BeautifulSoup(text, 'html.parser')
        self.body = soup
        self.url = original_url

    def extract(self, fill_empty=False):
        rtn = []
        for form in self.get_forms():
            action = self.get_action(form)
            inputs = self.get_inputs(form)
            special = self.get_special(form, fill_empty)
            data = self.get_form_parameters(inputs, fill_empty)
            for item in special:
                data[item] = special[item]
            rtn.append([urlparse.urljoin(self.url, action), data])
        return rtn

    def get_special(self, form, fill_empty=False):
        results = {}
        inputs = form.find_all('textarea', {'name': True})
        for i in inputs:
            name = i['name']
            if i.text and len(i.text.strip()):
                results[name] = i.text
            else:
                if fill_empty:
                    value = self.generate_random(None, None)
                    results[name] = value
                else:
                    results[name] = ""

        inputs = form.find_all('select', {'name': True})
        for i in inputs:
            name = i['name']
            options = i.find_all('option', {'value': True})
            if len(options):
                results[name] = options[0]['value']
            else:
                if fill_empty:
                    value = self.generate_random(None, None)
                    results[name] = value
                else:
                    results[name] = ""
        return results

    def get_form_parameters(self, inputs, fill_empty):
        res = {}
        for inp in inputs:
            try:
                name = inp['name']
                input_type = inp['type'] if 'type' in inp.attrs else None

                value = None
                if 'value' in inp.attrs and len(inp['value']) > 0:
                    value = inp['value']
                elif fill_empty and input_type != "hidden":
                    value = self.generate_random(input_type, name)
                else:
                    value = ""
                if name not in res:
                    res[name] = value
            except Exception as e:
                pass
        return res

    def generate_random(self, input_type, name):
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

    def get_inputs(self, form):
        inputs = form.find_all('input', {'name': True})
        return inputs

    def get_action(self, form):
        if 'action' not in form.attrs:
            return self.url
        return urlparse.urljoin(self.url, form['action'])

    def get_forms(self):
        forms = []
        try:
            forms = self.body.find_all('form')
        except:
            return forms
        return forms
