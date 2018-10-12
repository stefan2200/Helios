from selenium.common.exceptions import UnexpectedAlertPresentException, WebDriverException
from selenium.webdriver import Chrome, ChromeOptions
import re
import time
import logging
import sys
import os
import threading
from miproxy.proxy import RequestInterceptorPlugin, ResponseInterceptorPlugin, AsyncMitmProxy
from filelock import Timeout, FileLock


class GhostDriverInterface:
    driver_path = "drivers\\chromedriver.exe"
    driver = None
    logger = None
    page_sleep = 1.5

    def __init__(self, custom_path=None):
        if custom_path:
            self.driver_path = custom_path
        self.logger = logging.getLogger("WebDriver")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Starting Web Driver")
        if not os.path.exists(self.driver_path):
            self.logger.warning("Error loading driver from path: %s the driver module will be disabled\nGet the latest one from http://chromedriver.chromium.org/downloads" % self.driver_path)
            return
        self.start()

    def start(self, use_proxy=True, proxy_host="127.0.0.1", proxy_port=3333):
        options = ChromeOptions()

        options.add_argument("ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--headless")
        if use_proxy:
            self.logger.info("Enabled proxy %s:%d" % (proxy_host, proxy_port))
            options.add_argument("--proxy-server=http://" + "%s:%d" % (proxy_host, proxy_port))

        self.driver = Chrome(executable_path=self.driver_path, chrome_options=options)

    def get(self, url):
        if not self.driver:
            return
        self.logger.debug("GET %s" % url)
        try:
            self.driver.get(url)
        except UnexpectedAlertPresentException:
            alert = self.driver.switch_to.alert
            alert.accept()
            self.logger.warning("Page %s threw an alert. disposing and requesting page again" % url)
            self.driver.get(url)
        except Exception as e:
            raise
            self.logger.error("Page %s threw an error: %s" % (url, e.message))

        time.sleep(self.page_sleep)
        self.logger.debug("OK %s" % url)

    def close(self):
        self.logger.debug("Stopping Driver")
        if not self.driver:
            return
        self.driver.stop_client()
        self.driver.close()
        time.sleep(1)


class HTTPParser:

    @staticmethod
    def parse(request):
        request = request.strip()
        data = request.split('\r\n')
        method, path, _ = data[0].split()
        postdata = None
        if method == "POST" and data[len(data)-2] == "":
            postdata = data[len(data)-1]
            data = data[:-2]
        return method, data[1:], path, postdata

    @staticmethod
    def extract_host(headers):
        for row in headers:
            if ":" in row:
                key, value = row.split(':')
                key = key.strip()
                value = value.strip()
                if key.lower() == "host":
                    return value
        return ""

    @staticmethod
    def string_to_urltree(input, method_https=False):
        tree = []
        if input and len(input):
            for row in input.strip().split('\n'):
                method, host, url, data = row.split('\t')
                url = "http%s://%s%s" % ("s" if method_https else "", host, url)
                if method == "POST" and data != "0":
                    tree.append([url, HTTPParser.params_from_str(data)])
                else:
                    tree.append([url, None])
        return tree

    @staticmethod
    def params_from_str(string):
        out = {}
        if "&" in string:
            for param in string.split('&'):
                if "=" in param:
                    sub = param.split('=')
                    key = sub[0]
                    value = sub[1]
                    out[key] = value
                else:
                    out[key] = ""
        else:
            if "=" in string:
                sub = string.split('=')
                key = sub[0]
                value = sub[1]
                out[key] = value
            else:
                out[string] = ""
        return out


class DebugInterceptor(RequestInterceptorPlugin, ResponseInterceptorPlugin):
    proxy_log = "output.txt"
    proxy_log_lock = "output.txt.lock"

    def do_request(self, data):
        method, headers, path, postdata = HTTPParser.parse(data)
        host = HTTPParser.extract_host(headers)
        lock = FileLock(self.proxy_log_lock, timeout=1)
        with lock:
            lock.acquire()
            with open(self.proxy_log, 'a') as f:
                f.write("%s\t%s\t%s\t%s\n" % (method, host, path, postdata if postdata else "0"))
            lock.release()
        return data

    def do_response(self, data):
        return data

class CustomProxy:
    proxyThread = None
    proxy_host = '127.0.0.1'
    proxy_port = 3333
    logger = logging.getLogger("Proxy")
    proxy = None
    ca_file = ""
    ca_dir = ""
    proxy_log = "output.txt"

    def __init__(self, custom_path=None, cert=None):
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.debug("Loaded Proxy")
        if custom_path:
            self.ca_dir = custom_path
        if cert:
            self.ca_file = cert
        self.logger.debug("Cleaning proxy log: %s" % self.proxy_log)
        with open(self.proxy_log, 'w') as f:
            f.write("")

    def start(self):
        self.proxyThread = threading.Thread(target=self.subroutine)
        self.logger.debug("Starting Proxy")
        self.proxyThread.start()
        time.sleep(1)

    def subroutine(self):
        if self.ca_file:
            self.proxy = AsyncMitmProxy(ca_file=os.path.join(self.ca_dir, self.ca_file), server_address=(self.proxy_host, self.proxy_port))
        else:
            self.proxy = AsyncMitmProxy()
        self.proxy.register_interceptor(DebugInterceptor)
        try:
            self.proxy.serve_forever()
        except:
            print("The proxy has stopped")


class mefjus:
    seen = []
    ca_dir = "certs"
    ca_file = "mefjus.pem"

    def __init__(self):
        self.p = CustomProxy()
        self.x = GhostDriverInterface()

    def close(self):
        self.x.close()
        time.sleep(1)
        self.p.proxy.server_close()

    def run(self, urls):
        self.p.ca_dir = self.ca_dir
        if not os.path.exists(self.p.ca_dir):
            os.mkdir(self.p.ca_dir)
        self.p.ca_file = self.ca_file
        self.p.start()
        for url in urls:
            if type(url) is list:
                url = url[0]
            if url not in self.seen:
                self.seen.append(url)
                self.x.get(url)
        self.close()
        return self.read_output()

    def read_output(self):
        with open('output.txt') as f:
            tree = HTTPParser.string_to_urltree(f.read())
            return tree
        return ""
