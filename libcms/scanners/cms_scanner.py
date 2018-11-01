import time
import requests
import os
import logging
import sys

class Scanner:
    # set frequency for update call
    update_frequency = 0
    name = ""
    aggressive = False
    last_update = 0
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    logger = None
    updates = {}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36"}
    cookies = {}

    def get_version(self, url):
        return None

    def set_logger(self, log_level=logging.DEBUG):
        self.logger = logging.getLogger("CMS-%s" % self.name)
        self.logger.setLevel(log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)

    def update(self):
        pass
    
    def run(self, url):
        return {}

    def get_update_cache(self):
        if os.path.exists(self.cache_file('updates.txt')):
            self.logger.debug("Reading update cache")
            with open(self.cache_file('updates.txt'), 'r') as f:
                for x in f.read().strip().split('\n'):
                    if len(x):
                        scanner, last_update = x.split(':')
                        self.updates[scanner] = int(last_update)
                    else:
                        self.logger.warning("There appears to be an error in the updates cache file")
                        self.updates[self.name] = 0
            if self.name in self.updates:
                self.last_update = self.updates[self.name]
            else:
                self.updates[self.name] = time.time()
        else:
            self.logger.debug("No updates cache file found, creating empty one")
            self.updates[self.name] = time.time()

    def set_update_cache(self):
        self.logger.debug("Updating updates cache file")
        with open(self.cache_file('updates.txt'), 'w') as f:
            for x in self.updates:
                f.write("%s:%d\n" % (x, self.updates[x]))

    def cache_file(self, r):
        return os.path.join(self.cache_dir, r)

    def setup(self):
        if not os.path.exists(self.cache_dir):
            self.logger.info("Creating cache directory")
            os.mkdir(self.cache_dir)
        self.get_update_cache()
        if self.last_update + self.update_frequency < time.time():
            self.last_update = time.time()
            self.updates[self.name] = time.time()
            self.update()
            self.set_update_cache()
        else:
            self.logger.debug("Database is up to date, skipping..")

    def match_versions(self, version, fixed_in):
        if version == fixed_in:
            return False
        parts_version = version.split('.')
        parts_fixed_in = fixed_in.split('.')

        if len(parts_version) <= len(parts_fixed_in):
            for x in range(len(parts_version)):
                if int(parts_version[x]) < int(parts_fixed_in[x]):
                    return True
                if int(parts_version[x]) > int(parts_fixed_in[x]):
                    return False
            return False

        else:
            for x in range(len(parts_fixed_in)):
                if int(parts_version[x]) < int(parts_fixed_in[x]):
                    return True
                if int(parts_version[x]) > int(parts_fixed_in[x]):
                    return False
            return False

    def get(self, url, data=None):
        if not data:
            result = requests.get(url, allow_redirects=False, headers=self.headers, cookies=self.cookies)
            return result
        else:
            result = requests.post(url, data=data, allow_redirects=False, headers=self.headers, cookies=self.cookies)
            return result
