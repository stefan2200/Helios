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
try:
    import urlparse
except ImportError:
    # python 3 imports
    import urllib.parse as urlparse


class Helios:
    use_crawler = True
    use_scanner = True
    use_web_driver = False
    use_scripts = True
    use_adv_scripts = True
    crawler_max_urls = 200
    output_file = None

    user_agent = None
    scanoptions = []

    def __init__(self):
        self.logger = logging.getLogger("Helios")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.debug("Starting Helios")

    def run(self, starturl):
        start = [starturl, None]
        starttime = time.time()
        scope = Scope(starturl)
        loader = Modules.CustomModuleLoader()

        todo = []
        if self.use_crawler:
            c = Crawler(base_url=starturl)
            c.max_urls = self.crawler_max_urls
            # discovery scripts, pre-run scripts and advanced modules
            if self.use_scripts:
                s = ScriptEngine()

                self.logger.info("Starting filesystem discovery (pre-crawler)")
                new_links = s.run_fs(starturl)

                for newlink in new_links:
                    c.to_crawl.put(newlink)
                if self.use_adv_scripts:
                    self.logger.info("Running custom scripts")
                    links = loader.base_crawler(starturl)
                    for link in links:
                        self.logger.debug("Adding link %s from post scripts" % link)
                        c.to_crawl.put([link, None])

            self.logger.info("Starting Crawler")
            c.run_scraper()

            self.logger.info("Creating unique link/post data list")
            todo = uniquinize(c.scraped_pages)
            if self.use_web_driver:
                self.logger.info("Running GhostDriver")

                m = mefjus()
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
            todo = [starturl, None]
        if self.use_scanner:
            self.logger.info("Starting scan sequence")
            for page in todo:
                url, data = page
                self.logger.debug("[Scripts] Testing %s %s" % (url, data))
                req = Request(url, data=data, agent=self.user_agent)
                req.run()
                s.run_scripts(req)
            if self.use_adv_scripts:
                self.logger.info("Running post scripts")
                post_results = loader.run_post(todo)

        scan_tree = {
            'start': starttime,
            'end': time.time(),
            'scope': scope.host,
            'starturl': starturl,
            'crawled': len(c.scraped_pages),
            'scanned': len(todo) if self.use_scanner else 0,
            'results': s.results if self.use_scanner else [],
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
    parser.add_argument('--max-urls', help='Set max urls for the crawler', dest='maxurls', default=None)
    parser.add_argument('-a', '--all', help='Run everything', dest='allin', default=None, action='store_true')

    parser.add_argument('-s', '--scan', help='Enable the scanner', dest='scanner',
                        default=False, action='store_true')
    parser.add_argument('--adv', help='Enable the advanced scripts', dest='modules',
                        default=False, action='store_true')
    parser.add_argument('-o', '--output', help='Output file to write to (JSON)', dest='outfile', default=None)
    parser.add_argument('--scripts', help='Enable the script engine', dest='scripts', default=False, action='store_true')
    parser.add_argument('--options', help='Comma separated list of scan options', dest='options',
                        default=None)
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
    helios.use_web_driver = opts.driver
    helios.output_file = opts.outfile
    if opts.maxurls:
        helios.crawler_max_urls = int(opts.maxurls)
    helios.run(url)
