from Parser import *
from Request import Request
from Crawler import Crawler
from Utils import uniquinize
import json
from mefjus.ghost import mefjus
from Scope import Scope
import Modules
import time
import logging
import sys
import argparse
import Scanner
from metamonster import metamonster
try:
    import urlparse
except ImportError:
    # python 3 imports
    import urllib.parse as urlparse


class Helios:
    logger = None
    use_crawler = True
    use_scanner = True
    use_web_driver = False
    use_scripts = True
    use_adv_scripts = True
    crawler_max_urls = 200
    output_file = None
    log_level = logging.INFO
    driver_path = None
    _max_safe_threads = 10
    thread_count = 10

    proxy_port = 3333
    driver_show = False

    use_proxy = True

    user_agent = None
    scanoptions = None

    msf = False
    msf_host = "localhost"
    msf_port = 55553
    msf_username = "msf"
    msf_password = "msfrpcd"
    msf_ssl = True
    msf_path = "/api/"
    msf_autostart = False

    def start(self):
        self.logger = logging.getLogger("Helios")
        self.logger.setLevel(self.log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(self.log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.info("Starting Helios")
        if self.thread_count > self._max_safe_threads:
            self.logger.warning("Number of threads %d is too high, defaulting to %d" % (self.thread_count, self._max_safe_threads))
            self.thread_count = self._max_safe_threads

    def run(self, start_url):
        self.start()
        start_time = time.time()
        scope = Scope(start_url)
        c = None
        self.logger.debug("Parsing scan options")
        if self.scanoptions:
            vars = self.scanoptions.split(',')
            self.scanoptions = []
            for v in vars:
                opt = v.strip()
                self.scanoptions.append(opt)
                self.logger.debug("Enabled option %s" % opt)

        loader = Modules.CustomModuleLoader(options=helios.scanoptions, logger=self.log_level)

        todo = []
        if self.use_crawler:
            c = Crawler(base_url=start_url, logger=self.log_level)
            c.thread_count = self.thread_count
            c.max_urls = self.crawler_max_urls
            # discovery scripts, pre-run scripts and advanced modules
            if self.use_scripts:
                s = ScriptEngine(options=helios.scanoptions, logger=self.log_level)

                self.logger.info("Starting filesystem discovery (pre-crawler)")
                new_links = s.run_fs(start_url)

                for newlink in new_links:
                    c.to_crawl.put(newlink)
                if self.use_adv_scripts:
                    self.logger.info("Running custom scripts")
                    links = loader.base_crawler(start_url)
                    for link in links:
                        self.logger.debug("Adding link %s from post scripts" % link)
                        c.to_crawl.put([link, None])

            self.logger.info("Starting Crawler")
            c.run_scraper()

            self.logger.info("Creating unique link/post data list")
            todo = uniquinize(c.scraped_pages)
            if self.use_web_driver:
                self.logger.info("Running GhostDriver")

                m = mefjus(logger=self.log_level, driver_path=self.driver_path, use_proxy=self.use_proxy, proxy_port=self.proxy_port, use_https=scope.is_https)
                m.show_browser = self.driver_show
                results = m.run(todo)
                for res in results:
                    if not scope.in_scope(res[0]):
                        self.logger.debug("IGNORE %s.. out-of-scope" % res)
                        continue
                    if c.get_filetype(res[0]) not in c.allowed_filetypes:
                        self.logger.debug("IGNORE %s.. bad file-type" % res)
                        continue
                    if res in c.scraped_pages:
                        self.logger.debug("IGNORE %s.. exists" % res)
                        continue
                    else:
                        todo.append(res)
                        self.logger.debug("QUEUE %s" % res)
                self.logger.info("Creating unique link/post data list")
                old_num = len(todo)
                todo = uniquinize(todo)
                self.logger.debug("WebDriver discovered %d more url/post data pairs" % (len(todo) - old_num))
        else:
            todo = [start_url, None]
        scanner = None
        if self.use_scanner:
            self.logger.info("Starting scan sequence")
            scanner = Scanner.Scanner(logger=self.log_level, script_engine=s, thread_count=self.thread_count)
            for page in todo:
                url, data = page
                req = Request(url, data=data, agent=self.user_agent)
                req.run()
                scanner.queue.put(req)
                scanner.logger.debug("Queued %s %s" % (url, data))
            scanner.run()
            if self.use_adv_scripts:
                loader.logger.info("Running post scripts")
                post_results = loader.run_post(todo)
        meta = {}
        if self.msf:
            monster = metamonster.MetaMonster(log_level=self.log_level)
            monster.username = self.msf_username
            monster.password = self.msf_password
            monster.host = self.msf_host
            monster.port = self.msf_port
            monster.ssl = self.msf_ssl
            monster.endpoint = self.msf_path
            monster.should_start = self.msf_autostart

            monster.connect(start_url)
            if monster.client and monster.client.is_working:
                monster.get_exploits()
                monster.detect()
                queries = monster.create_queries()
                monster.run_queries(queries)
                meta = monster.results


        scan_tree = {
            'start': start_time,
            'end': time.time(),
            'scope': scope.host,
            'starturl': start_url,
            'crawled': len(c.scraped_pages) if c else 0,
            'scanned': len(todo) if self.use_scanner else 0,
            'results': scanner.script_engine.results if scanner else [],
            'metasploit': meta,
            'post': post_results if self.use_adv_scripts else []
        }

        if not self.output_file:
            with open('scan_results_%s.json' % scope.host, 'w') as f:
                f.write(json.dumps(scan_tree))
                self.logger.info("Wrote results to scan_results_%s.json" % scope.host)
        else:
            with open(self.output_file, 'w') as f:
                f.write(json.dumps(scan_tree))
                self.logger.info("Wrote results to %s" % self.output_file)


if __name__ == "__main__":
    usage = """%s: args""" % sys.argv[0]
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('-u', '--url', help='URL to start with', dest='url', required=True)
    parser.add_argument('--user-agent', help='Set the user agent', dest='user_agent', default=None)
    parser.add_argument('-c', '--crawl', help='Enable the crawler', dest='crawler', action='store_true')
    parser.add_argument('-d', '--driver', help='Run WebDriver for advanced discovery', dest='driver', action='store_true')
    parser.add_argument('--driver-path', help='Set custom path for the WebDriver', dest='driver_path', default=None)
    parser.add_argument('--show-driver', help='Show the WebDriver window', dest='show_driver', default=None, action='store_true')
    parser.add_argument('--max-urls', help='Set max urls for the crawler', dest='maxurls', default=None)
    parser.add_argument('-a', '--all', help='Run everything', dest='allin', default=None, action='store_true')

    parser.add_argument('--no-proxy', help='Disable the proxy module for the WebDriver', dest='no_proxy', action='store_true')
    parser.add_argument('--proxy-port', help='Set a custom port for the proxy module, default: 3333', dest='proxy_port',
                        default=None)
    parser.add_argument('--threads', help='Set a custom number of crawling / scanning threads', dest='threads',
                        default=None)

    parser.add_argument('-s', '--scan', help='Enable the scanner', dest='scanner',
                        default=False, action='store_true')
    parser.add_argument('--adv', help='Enable the advanced scripts', dest='modules',
                        default=False, action='store_true')
    parser.add_argument('-o', '--output', help='Output file to write to (JSON)', dest='outfile', default=None)
    parser.add_argument('--scripts', help='Enable the script engine', dest='scripts', default=False, action='store_true')
    parser.add_argument('--options', help='Comma separated list of scan options (discovery, passive, injection, dangerous, all)', dest='custom_options',
                        default=None)
    parser.add_argument('--msf', help='Enable the msfrpcd exploit module', dest='msf', default=False,
                        action='store_true')
    parser.add_argument('--msf-host', help='Set the msfrpcd host', dest='msf_host', default=None)
    parser.add_argument('--msf-port', help='Set the msfrpcd port', dest='msf_port', default=None)
    parser.add_argument('--msf-creds', help='Set the msfrpcd username:password', dest='msf_creds', default=None)
    parser.add_argument('--msf-endpoint', help='Set a custom endpoint URI', dest='msf_uri', default=None)
    parser.add_argument('--msf-nossl', help='Disable SSL', dest='msf_nossl', default=False)
    parser.add_argument('--msf-start', help='Start msfrpcd if not running already', dest='msf_autostart', default=False,
                        action='store_true')
    parser.add_argument('-v', '--verbose', help='Verbose mode', dest='verbose', default=False, action='store_true')

    opts = parser.parse_args(sys.argv[1:])

    url = opts.url
    helios = Helios()
    helios.user_agent = opts.user_agent
    if not opts.allin:
        helios.use_scanner = opts.scanner
        helios.use_scripts = opts.scripts
        helios.use_adv_scripts = opts.modules
        helios.use_crawler = opts.crawler
    helios.scanoptions = opts.custom_options
    helios.use_web_driver = opts.driver
    helios.driver_path = opts.driver_path
    helios.driver_show = opts.show_driver
    helios.use_proxy = not opts.no_proxy
    if opts.proxy_port:
        helios.proxy_port = int(opts.proxy_port)
    helios.driver_show = opts.show_driver
    helios.output_file = opts.outfile
    if opts.verbose:
        helios.log_level = logging.DEBUG
    if opts.threads:
        helios.thread_count = int(opts.threads)
    if opts.maxurls:
        helios.crawler_max_urls = int(opts.maxurls)
    if opts.msf:
        helios.msf = True
        if opts.msf_creds:
            helios.msf_username, helios.msf_password = opts.msf_creds.split(':')
        if opts.msf_port:
            helios.msf_port = int(opts.msf_port)
        if opts.msf_host:
            helios.msf_host = opts.msf_host
        if opts.msf_nossl:
            helios.msf_ssl = False
        if opts.msf_autostart:
            helios.msf_ssl = False
        if opts.msf_uri:
            helios.msf_path = opts.msf_uri
    helios.run(url)
