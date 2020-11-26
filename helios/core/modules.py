import os
import logging
import sys
import json


class CustomModuleLoader:
    folder = ""
    blacklist = ['module_base.py', '__init__.py']
    modules = []
    logger = None
    options = None
    writer = None
    scope = None
    sslverify = False
    headers = {}
    cookies = {}

    def __init__(self, folder='helios/modules', blacklist=[], options=None, logger=logging.INFO, database=None, scope=None):
        folder = os.path.join(os.path.dirname(__file__), '..', 'modules')
        self.blacklist.extend(blacklist)
        self.options = options
        self.folder = folder
        self.logger = logging.getLogger("CustomModuleLoader")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Loading custom modules")
        self.scope = scope
        self.load_modules()
        self.writer = database

    def load(self, f):
        base = f.replace('.py', '')
        try:
            command_module = __import__("helios.modules.%s" % base, fromlist=["modules"])
            module = command_module.Module()
            if self.options:
                if 'all' not in self.options:
                    for opt in module.module_types:
                        if opt not in self.options:
                            self.logger.debug("Disabling module %s because %s is not enabled" % (module.name, opt))
                            return
            else:
                if 'dangerous' in module.module_types:
                    self.logger.debug(
                        "Disabling script %s because dangerous flag is present, "
                        "use --options all or add the dangerous flag to override" % (
                            module.name))
                    return
            module.scope = self.scope
            module.verify = self.sslverify
            module.headers = self.headers
            module.cookies = self.cookies
            self.modules.append(module)
            self.logger.debug("Enabled module: %s" % f)
        except ImportError as e:
            self.logger.warning("Error importing module:%s %s" % (f, str(e)))
        except Exception as e:
            self.logger.warning("Error loading module:%s %s" % (f, str(e)))

    def load_modules(self):
        for f in os.listdir(self.folder):
            if not f.endswith('.py'):
                continue
            if f in self.blacklist:
                continue
            self.load(f)

    def run_post(self, urltree, headers={}, cookies={}):
        output = []
        for module in self.modules:
            if 1:
                if module.input == "urldata":
                    for row in urltree:
                        try:
                            url, data = row
                            self.logger.debug("Running module %s on url: %s" % (module.name, url))
                            results = module.run(url, data, headers, cookies)
                            if results and len(results):
                                for r in results:
                                    if self.writer:
                                        self.writer.put(result_type="Module - Adv", script=module.name,
                                                    severity=module.severity, text=json.dumps(r))
                                    self.logger.info("Module %s Discovered %s" % (module.name, r))
                                    output.extend([module.name, r])
                        except Exception as e:
                            self.logger.warning("Error executing module %s on %s %s: %s" % (module.name, url, data, str(e)))
                if module.input == "urls":
                    self.logger.debug("Running module %s on %d urls" % (module.name, len(urltree)))
                    try:
                        results = module.run(urltree, headers, cookies)
                        if results and len(results):
                            for r in results:
                                self.logger.info("Module %s Discovered %s" % (module.name, r))
                                if self.writer:
                                    self.writer.put(result_type="Module - Adv", script=module.name,
                                                    severity=module.severity, text=json.dumps(r))
                                output.extend([module.name, r])
                    except Exception as e:
                        self.logger.warning("Error executing module %s on urls: %s" % (module.name, str(e)))

        return output

    def base_crawler(self, base):
        output = []
        for module in self.modules:
            if module.input == "base" and module.output == "crawler":
                self.logger.debug("Running pre-crawl module %s on base url %s" % (module.name, base))
                results = module.run(base)
                output.extend(results)
        return output
