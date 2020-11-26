import time
import logging
import sys
import os
import threading

from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver import Chrome, ChromeOptions
from filelock import FileLock

from helios.ext.mefjus.proxy import *


class GhostDriverInterface:
    driver_path = "drivers\\chromedriver.exe"
    driver = None
    logger = None
    page_sleep = 2
    proxy_host = "127.0.0.1"
    proxy_port = 3333

    def __init__(self, custom_path=None, logger=None, show_browser=False, use_proxy=True, proxy_port=None):
        if custom_path:
            self.driver_path = custom_path
        else:
            current_fp = os.path.abspath(os.path.dirname(__file__))
            self.driver_path = os.path.join(current_fp, "../../drivers/chromedriver.exe")
        if proxy_port:
            self.proxy_port = int(proxy_port)
        self.logger = logging.getLogger("WebDriver")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Starting Web Driver")
        if not os.path.exists(self.driver_path):
            self.logger.warning("Error loading driver from path: %s the driver module will be disabled\n"
                                "Get the latest one from http://chromedriver.chromium.org/downloads" % self.driver_path)
            return
        self.start(use_proxy=use_proxy, show_browser=show_browser)

    def start(self, use_proxy=True, show_browser=False):
        try:
            options = ChromeOptions()
            options.add_argument("ignore-certificate-errors")
            options.add_argument("--ignore-ssl-errors")
            if not show_browser:
                options.add_argument("--headless")
            if use_proxy:
                self.logger.info("Enabled proxy %s:%d" % (self.proxy_host, self.proxy_port))
                options.add_argument("--proxy-server=http://" + "%s:%d" % (self.proxy_host, self.proxy_port))

            self.driver = Chrome(executable_path=self.driver_path, chrome_options=options)
        except Exception as e:
            self.logger.error("Error creating WebDriver object: %s" % str(e))

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
            self.logger.error("Page %s threw an error: %s" % (url, str(e)))

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
                pairs = row.split(':')
                if len(pairs) > 2:
                    continue
                key, value = pairs[0], pairs[1]
                key = key.strip()
                value = value.strip()
                if key.lower() == "host":
                    return value
        return ""

    @staticmethod
    def string_to_urltree(input, use_https=False):
        tree = []
        if input and len(input):
            for row in input.strip().split('\n'):
                try:
                    method, host, url, data = row.split('\t')
                    url = "http%s://%s%s" % ("s" if use_https else "", host, url)
                    if method == "POST" and data != "0":
                        tree.append([url, HTTPParser.params_from_str(data)])
                    else:
                        tree.append([url, None])
                except Exception as e:
                    pass
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
        lock = FileLock(self.proxy_log_lock, timeout=5)
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

    def __init__(self, custom_path=None, cert=None, logger=logging.INFO, proxy_port=None):
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if proxy_port:
            self.proxy_port = int(proxy_port)
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
            return


class Mefjus:
    seen = []
    ca_dir = "certs"
    ca_file = "mefjus.pem"
    proxy = None
    driver = None
    show_browser = None

    def __init__(self, logger=logging.INFO, driver_path=None, proxy_port=3333, use_proxy=True, use_https=True, show_driver=False):
        if use_proxy:
            self.proxy = CustomProxy(logger=logger, proxy_port=proxy_port)
        self.driver = GhostDriverInterface(logger=logger, custom_path=driver_path, proxy_port=proxy_port, use_proxy=use_proxy, show_browser=show_driver)
        self.use_https = use_https

    def close(self):
        if self.driver:
            self.driver.close()
            time.sleep(1)
        if self.proxy:
            self.proxy.proxy.server_close()

    def run(self, urls, interactive=False):
        if self.proxy:
            self.proxy.ca_dir = self.ca_dir
            if not os.path.exists(self.proxy.ca_dir):
                os.mkdir(self.proxy.ca_dir)
            self.proxy.ca_file = self.ca_file
            self.proxy.start()
        for url in urls:
            if type(url) is list:
                url = url[0]
            if url not in self.seen:
                self.seen.append(url)
                self.driver.get(url)
        if interactive:
            print("Interactive mode enabled, the browser will continue to function and log proxy-request.")
            print("Press any key to continue")
            try:
                x = input()
            except:
                pass
        self.close()
        return self.read_output()

    def read_output(self):
        with open('output.txt') as f:
            tree = HTTPParser.string_to_urltree(f.read(), use_https=self.use_https)
            return tree
