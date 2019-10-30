from core.Scripts import *
from core.Request import Request
from core.Crawler import Crawler
from core.Utils import uniquinize
from core.Output import SQLiteWriter
from core.WebApps import WebAppModuleLoader
import json
from ext.mefjus.ghost import Mefjus
from core.Scope import Scope
from core import Modules, Scanner
import time
import logging
import sys
import argparse
import ext.libcms.cms_scanner_core
import urllib3
from ext.metamonster import metamonster
try:
    import urlparse
except ImportError:
    # python 3 imports
    import urllib.parse as urlparse

urllib3.disable_warnings()


class Helios:
    logger = None
    crawler_max_urls = 200
    output_file = None
    _max_safe_threads = 25
    thread_count = 10

    proxy_port = 3333
    driver_show = False

    use_proxy = True
    db = None
    scan_cookies = {}
    options = None

    def __init__(self, options):
        self.options = options

    def start(self):
        self.logger = logging.getLogger("Helios")
        self.logger.setLevel(logging.DEBUG if self.options.verbose else logging.INFO)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG if self.options.verbose else logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.info("Starting Helios")

        try:
            self.thread_count = int(self.options.threads)
        except:
            # None or invalid format
            pass
        if self.thread_count > self._max_safe_threads:
            self.logger.warning("Number of threads %d is too high, defaulting to %d" %
                                (self.thread_count, self._max_safe_threads))
            self.thread_count = self._max_safe_threads

        self.db = SQLiteWriter()
        self.db.open_db(self.options.db)
        self.logger.info("Using SQLite database %s" % self.options.db)

    def run(self, start_urls, scopes=None):
        start_url = start_urls[0]
        self.start()
        start_time = time.time()
        scope = Scope(start_url, options=self.options.scope_options)
        if scopes:
            scope.scopes = [x.strip() for x in scopes.split(',')]
        self.db.start(start_url, scope.host)
        c = None
        s = None
        loader = None
        self.logger.debug("Parsing scan options")
        scanoptions = []
        if self.options.custom_options:
            scan_vars = self.options.custom_options.split(',')
            for v in scan_vars:
                opt = v.strip()
                scanoptions.append(opt)
                self.logger.debug("Enabled option %s" % opt)
        if self.options.scanner or self.options.allin:
            s = ScriptEngine(options=scanoptions, logger=self.logger.getEffectiveLevel(), database=self.db)

        if self.options.use_adv_scripts or self.options.allin:
            loader = Modules.CustomModuleLoader(options=scanoptions,
                                                logger=self.logger.getEffectiveLevel(),
                                                database=self.db)

        todo = []
        c = Crawler(base_url=start_url, logger=self.logger.getEffectiveLevel())
        if self.options.use_crawler or self.options.allin:

            c.thread_count = self.thread_count
            c.max_urls = int(self.options.maxurls)
            c.scope = scope
            if self.options.user_agent:
                c.headers = {'User-Agent': self.options.user_agent}
            if len(start_urls) != 1:
                for extra_url in start_urls[1:]:
                    c.parse_url(extra_url, extra_url)
            # discovery scripts, pre-run scripts and advanced modules
            if self.options.scanner or self.options.allin:
                self.logger.info("Starting filesystem discovery (pre-crawler)")
                new_links = s.run_fs(start_url)

                for newlink in new_links:
                    c.parse_url(newlink[0], newlink[0])
                if self.options.use_adv_scripts or self.options.allin:
                    self.logger.info("Running custom scripts (pre-crawler)")
                    links = loader.base_crawler(start_url)
                    for link in links:
                        self.logger.debug("Adding link %s from post scripts" % link)
                        c.parse_url(link, link)

            self.logger.info("Starting Crawler")
            c.run_scraper()
            self.logger.debug("Cookies set during scan: %s" % (str(c.cookie.cookies)))
            self.scan_cookies = c.cookie.cookies

            self.logger.info("Creating unique link/post data list")
            todo = uniquinize(c.scraped_pages)
        else:
            todo = [[start_url, None]]

        if self.options.driver:
            self.logger.info("Running GhostDriver")

            m = Mefjus(logger=self.logger.getEffectiveLevel(),
                       driver_path=self.options.driver_path,
                       use_proxy=self.options.proxy,
                       proxy_port=self.options.proxy_port,
                       use_https=scope.is_https,
                       show_driver=self.options.show_driver or self.options.interactive)
            results = m.run(todo, interactive=self.options.interactive)
            for res in results:
                if not scope.in_scope(res[0]):
                    self.logger.debug("IGNORE %s.. out-of-scope" % res)
                    continue
                if c.get_filetype(res[0]) in c.blocked_filetypes:
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

        scanner = None
        if self.options.scanner or self.options.allin:
            self.logger.info("Starting scan sequence")
            if len(todo) < self.thread_count:
                # for performance sake
                self.thread_count = len(todo)
            scanner = Scanner.Scanner(logger=self.logger.getEffectiveLevel(),
                                      script_engine=s,
                                      thread_count=self.thread_count)
            for page in todo:
                url, data = page
                req = Request(url, data=data, agent=self.options.user_agent)
                req.run()
                scanner.queue.put(req)
                scanner.logger.debug("Queued %s %s" % (url, data))
            scanner.run()

        post_results = []
        if self.options.use_adv_scripts or self.options.allin:
            self.logger.info("Running post scripts")
            post_results = loader.run_post(todo, cookies=self.scan_cookies)
        cms_results = None
        if self.options.cms_enabled or self.options.allin:
            cms_loader = ext.libcms.cms_scanner_core.CustomModuleLoader(log_level=self.logger.getEffectiveLevel())
            cms_results = cms_loader.run_scripts(start_url)
            if cms_results:
                for cms in cms_results:
                    for cms_result in cms_results[cms]:
                        self.db.put(result_type="CMS Script", script=cms,
                                    severity=0, text=cms_result)

        webapp_results = None
        if self.options.webapp_enabled or self.options.allin:
            webapp_loader = WebAppModuleLoader(log_level=self.logger.getEffectiveLevel())
            webapp_loader.load_modules()
            webapp_results = webapp_loader.run_scripts(start_url, scope=scope, cookies=self.scan_cookies)
            if webapp_results:
                for webapp in webapp_results:
                    for webapp_result in webapp_results[webapp]:
                        self.db.put(result_type="WebApp Script", script=webapp,
                                    severity=0, text=json.dumps(webapp_result))
        meta = {}
        if self.options.msf:
            monster = metamonster.MetaMonster(log_level=self.logger.getEffectiveLevel())
            creds = self.options.msf_creds.split(':')
            monster.username = creds[0]
            monster.password = creds[1]
            monster.host = self.options.msf_host
            monster.port = self.options.msf_port
            monster.ssl = self.options.msf_ssl
            monster.endpoint = self.options.msf_uri
            monster.should_start = self.options.msf_autostart

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
            'scanned': len(todo) if self.options.scanner else 0,
            'results': scanner.script_engine.results if scanner else [],
            'metasploit': meta,
            'cms': cms_results,
            'webapps': webapp_results,
            'post': post_results if self.options.use_adv_scripts else []
        }

        self.db.end()

        if self.options.outfile:
            with open(self.options.outfile, 'w') as f:
                f.write(json.dumps(scan_tree))
                self.logger.info("Wrote results to %s" % self.options.outfile)


if __name__ == "__main__":
    usage = """%s: args""" % sys.argv[0]
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('-u', '--url', help='URL to start with', dest='url', default=None)
    parser.add_argument('--urls', help='file with URL\'s to start with', dest='urls', default=None)
    parser.add_argument('--user-agent', help='Set the user agent', dest='user_agent', default=None)
    parser.add_argument('-c', '--crawler', help='Enable the crawler', dest='use_crawler', action='store_true')
    parser.add_argument('-d', '--driver', help='Run WebDriver for advanced discovery',
                        dest='driver', action='store_true')
    parser.add_argument('--cms', help='Enable the CMS module', dest='cms_enabled', action='store_true', default=False)
    parser.add_argument('--webapp', help='Enable scanning of web application frameworks like Tomcat / Jboss',
                        dest='webapp_enabled', action='store_true', default=False)
    parser.add_argument('--driver-path', help='Set custom path for the WebDriver', dest='driver_path', default=None)
    parser.add_argument('--show-driver', help='Show the WebDriver window', dest='show_driver',
                        default=None, action='store_true')
    parser.add_argument('--interactive', help='Dont close the WebDriver window until keypress',
                        dest='interactive', default=False,
                        action='store_true')
    parser.add_argument('--max-urls', help='Set max urls for the crawler', dest='maxurls', default=200)
    parser.add_argument('-a', '--all', help='Run everything', dest='allin', default=None, action='store_true')
    parser.add_argument('--scopes', help='Extra allowed scopes, comma separated hostnames (* can be used to wildcard)',
                        dest='scopes', default=None)
    parser.add_argument('--scope-options', help='Various scope options',
                        dest='scope_options', default=None)

    parser.add_argument('--no-proxy', help='Disable the proxy module for the WebDriver', dest='proxy',
                        action='store_false', default=True)
    parser.add_argument('--proxy-port', help='Set a custom port for the proxy module, default: 3333', dest='proxy_port',
                        default=None)
    parser.add_argument('--threads', help='Set a custom number of crawling / scanning threads', dest='threads',
                        default=None)

    parser.add_argument('-s', '--scan', help='Enable the scanner', dest='scanner',
                        default=False, action='store_true')
    parser.add_argument('--adv', help='Enable the advanced scripts', dest='use_adv_scripts',
                        default=False, action='store_true')
    parser.add_argument('--database', help='The SQLite database to use', dest='db', default="helios.db")
    parser.add_argument('-o', '--output', help='Output file to write to (JSON)', dest='outfile', default=None)
    parser.add_argument('--options',
                        help='Comma separated list of scan options (discovery, passive, injection, dangerous, all)',
                        dest='custom_options', default=None)
    parser.add_argument('--msf', help='Enable the msfrpcd exploit module', dest='msf', default=False,
                        action='store_true')
    parser.add_argument('--msf-host', help='Set the msfrpcd host', dest='msf_host', default="localhost")
    parser.add_argument('--msf-port', help='Set the msfrpcd port', dest='msf_port', default="55553")
    parser.add_argument('--msf-creds', help='Set the msfrpcd username:password',
                        dest='msf_creds', default="msf:msfrpcd")
    parser.add_argument('--msf-endpoint', help='Set a custom endpoint URI', dest='msf_uri', default="/api/")
    parser.add_argument('--msf-nossl', help='Disable SSL', dest='msf_nossl', default=False)
    parser.add_argument('--msf-start', help='Start msfrpcd if not running already', dest='msf_autostart', default=False,
                        action='store_true')
    parser.add_argument('-v', '--verbose', help='Verbose mode', dest='verbose', default=False, action='store_true')

    opts = parser.parse_args(sys.argv[1:])
    urls = []
    if not opts.url:
        if not opts.urls:
            print("-u or --urls is required to start")
            sys.exit(1)
        else:
            with open(opts.urls, 'r') as urlfile:
                urls = [x.strip() for x in urlfile.read().strip().split('\n')]
                print("Got %d start URL's from file %s" % (len(urls), opts.urls))
    else:
        urls = [opts.url]

    helios = Helios(opts)
    try:
        helios.run(urls, opts.scopes)
    except KeyboardInterrupt:
        helios.logger.warning("KeyboardInterrupt received, shutting down")
        helios.db.end()
    except Exception as e:
        if helios.options.verbose:
            helios.db.end()
            raise
        helios.logger.error(str(e))
        helios.logger.warning("Critical error received, shutting down")
        helios.db.end()
