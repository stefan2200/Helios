import os
import logging
import sys

from helios.ext.libcms.detector import CMSDetector


# Main module loader for CMS Scanners
class CustomModuleLoader:
    folder = ""
    blacklist = ['cms_scanner.py', '__init__.py']
    modules = []
    logger = None
    is_aggressive = False
    module = None
    # common paths for cms installations
    cms_sub = ['wordpress', 'wp', 'magento', 'joomla', 'blog', 'drupal']

    def __init__(self, folder='scanners', blacklist=[], is_aggressive=False, log_level=logging.INFO):
        self.blacklist.extend(blacklist)
        self.folder = os.path.join(os.path.dirname(__file__), folder)
        self.logger = logging.getLogger("CMS Scanner")
        self.logger.setLevel(log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Loading CMS scripts")
        self.is_aggressive = is_aggressive

    def load(self, script, name):
        sys.path.insert(0, os.path.dirname(__file__))
        base = script.replace('.py', '')
        try:
            command_module = __import__("scanners.%s" % base, fromlist=["scanners"])
            module = command_module.Scanner()
            if module.name == name:
                self.module = module
                self.module.set_logger(self.logger.getEffectiveLevel())
                self.logger.debug("Selected %s for target" % name)
        except ImportError as e:
            self.logger.warning("Error importing script:%s %s" % (base, str(e)))
        except Exception as e:
            self.logger.warning("Error loading script:%s %s" % (base, str(e)))

    def load_modules(self, name):
        for f in os.listdir(self.folder):
            if not f.endswith('.py'):
                continue
            if f in self.blacklist:
                continue
            self.load(f, name)

    def run_scripts(self, base, headers={}, cookies={}):
        p = CMSDetector()
        cms = p.scan(base)
        if cms:
            self.logger.debug("Detected %s as active CMS" % cms)
            self.load_modules(cms)
            if self.module:
                results = self.module.run(base)
                return {cms: results}
            else:
                self.logger.warning("No script was found for CMS %s" % cms)
        for cms_sub in self.cms_sub:
            cms = p.scan_sub(base, cms_sub)
            if cms:
                cms_url = "%s/%s/" % (base[:-1] if base.endswith('/') else base, cms_sub)
                self.logger.info("CMS %s was detected in folder %s" % (cms, cms_url))
                self.logger.debug("Detected %s as active CMS" % cms)
                self.load_modules(cms)
                if self.module:
                    results = self.module.run(cms_url)
                    return {cms: results}
                else:
                    self.logger.warning("No script was found for CMS %s" % cms)
                    return None


        else:
            self.logger.info("No CMS was detected on target %s" % base)
        return None

