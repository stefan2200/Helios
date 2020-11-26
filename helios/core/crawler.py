import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import time
import json
import random
import re
import string
import hashlib
import os
import sys

from helios.core.engine import CookieLib
from helios.core.utils import params_from_str

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
    blocked_filetypes = ['.jpg', '.png', '.gif', '.wav', '.mp3', '.mp4', '.3gp', '.js', '.css', '.jpeg', '.pdf', '.ico',
                         '.tiff', '.svg', '.doc', '.docx', '.xls', '.xlsx', '.woff', '.woff2', '.ttf', '.eot', '.ttf']
    output_filename = "tmp.json"
    thread_count = 5
    cookie = CookieLib()
    is_debug = True
    logger = None
    headers = {}
    data_dir = "data"
    page_re = [
        re.compile(r'window\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'document\.location\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'document\.location\.href\s*=\s*[\'"](.+?)[\'"]'),
        re.compile(r'window\.location\.replace\([\'"](.+?)[\'"]'),
        re.compile(r'http-equiv="refresh.+?URL=[\'"](.+?)[\'"]')
    ]
    write_output = True
    scope = None
    base_url = None
    login = None

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
        if self.login and 'logout' in url.lower():
            self.ignored.append(url)
            self.logger.debug("Url %s will be ignored because login is active" % url)
            return

        if 'manual/' in url.lower():
            self.ignored.append(url)
            return

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
        if result:
            if result.status_code == 200:
                self.parse_links(result.text, result.url)
                self.scrape_info(result.text, result.url)
                try:
                    self.cookie.autoparse(result.headers)
                except Exception as e:
                    self.logger.warning("Error processing page cookies: %s" % str(e))
            if str(result.status_code).startswith('3'):
                if 'Location' in result.headers:
                    self.parse_url(result.headers['Location'], result.url)

    def scrape_page(self, url):
        url, data = url
        try:
            if data:
                return requests.post(url, data, cookies=self.cookie.cookies,
                                     allow_redirects=False, headers=self.headers,  timeout=(3, 30), verify=False)
            return requests.get(url, timeout=(3, 30), cookies=self.cookie.cookies,
                                allow_redirects=False, headers=self.headers, verify=False)
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


# class for fast dir/file discovery using word list
class WebFinder:
    logger = None
    pool = Queue(maxsize=0)
    executor = None
    ok_status_codes = [200, 204, 301, 302, 307, 401, 403, 500]
    output = []
    errors = 0
    can_use_head = False
    invalid_text = None
    thread_count = 20
    cookies = {}
    headers = {}

    def __init__(self, url, logger, word_list=None, append=None, ok_status_codes=None, invalid_text=None, threads=20):
        self.logger = logging.getLogger("WebFinder")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        if not word_list:
            self.logger.info("No custom wordlist supplied, using seclists common one")
            cdir = os.path.abspath(os.path.dirname(__file__))
            word_list = os.path.join(cdir, "../wordlists/common.txt")
        if not os.path.exists(word_list):
            self.logger.error("Wordlist file %s could not be opened!" % word_list)
            return

        self.thread_count = threads

        with open(word_list, 'r') as input_file:
            for line in input_file.readlines():
                line = line.strip()
                self.pool.put(urlparse.urljoin(url, line))
                if append:
                    for ext in append.split(','):
                        ext = ext.strip()
                        if ext.startswith('.'):
                            ext = ext[1:]
                        self.pool.put(urlparse.urljoin(url, "%s.%s" % (line, ext)))
        self.logger.info("Queued %d items for file / directory discovery" % (self.pool.qsize()))
        if ok_status_codes:
            self.ok_status_codes = [int(x.strip()) for x in ok_status_codes.split(',')]

        if invalid_text:
            self.can_use_head = False
            self.invalid_text = invalid_text
        else:
            if self.detect_head(url):
                self.logger.debug("HEAD method appears to be usable")
            else:
                self.logger.debug("HEAD method does not appears to be usable")
            if self.detect_wildcard(url):
                self.logger.info("You can supply a 404 text pattern with the --wordlist-404 argument")
                return

        self.run()

    def run(self):
        with ThreadPoolExecutor(max_workers=self.thread_count) as executor:
            while 1:
                if self.errors > 40:
                    self.logger.error("Giving up because of timeout errors!")
                    self.pool.empty()
                    return

                if self.errors > 20:
                    self.logger.warning("Too many timeouts, waiting 60 seconds")
                    time.sleep(60)

                try:
                    url = self.pool.get(timeout=60)
                    job = executor.submit(self.check, url)
                    job.add_done_callback(self.result_callback)
                except Empty:
                    self.logger.debug("Run done, waiting for threads to finish")
                    time.sleep(5)
                    break
                except KeyboardInterrupt:
                    self.pool.empty()
                    break

    def result_callback(self, response):
        result = response.result()
        if result is False:
            return
        self.errors = 0
        if self.invalid_text and self.invalid_text not in result.text:
            self.output.append(result.url)
            self.logger.info("Discovered: %s [%d]" % (result.url, result.status_code))
        if result.status_code in self.ok_status_codes:
            self.output.append(result.url)
            self.logger.info("Discovered: %s [%d]" % (result.url, result.status_code))

    def detect_wildcard(self, url):
        try:
            rand_str = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase) for _ in range(15))
            invalid_url = urlparse.urljoin(url, rand_str)
            res = requests.get(url=invalid_url, allow_redirects=False)
            if res.status_code in self.ok_status_codes:
                self.logger.warning("Response code wildcard. detected %d on URL: %s" % (res.status_code, invalid_url))
                return True
        except Exception as e:
            pass
        return False

    def detect_head(self, url):
        try:
            res = requests.head(url=url, allow_redirects=False)
            if res.status_code != 405:
                self.can_use_head = True
                return True
        except Exception as e:
            self.logger.warning("Error detecting HEAD on URL %s: %s" % (url, str(e)))
            pass
        return False

    def check(self, url):
        try:
            if self.can_use_head:
                return requests.head(url, allow_redirects=False, headers=self.headers, cookies=self.cookies)
            else:
                return requests.get(url, allow_redirects=False, headers=self.headers, cookies=self.cookies)

        except requests.exceptions.ConnectTimeout:
            self.errors += 1
            self.pool.put(url)
            return False
        except requests.exceptions.ReadTimeout:
            self.errors += 1
            self.pool.put(url)
            return False
        except Exception as e:
            self.logger.warning("Warning: URLS %s causes exception: %s" % (url, str(e)))
            return False


# the Extractor class is used to extract forms from HTML
# the default extract() method is equipped with the functionality to automatically fill in input fields
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
