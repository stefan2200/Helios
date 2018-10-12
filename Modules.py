import os
import logging
import sys


class CustomModuleLoader:
    folder = ""
    blacklist = ['module_base.py', '__init__.py']
    modules = []
    logger = None

    def __init__(self, folder='modules', blacklist=[]):
        self.blacklist.extend(blacklist)
        self.folder = folder
        self.logger = logging.getLogger("CustomModuleLoader")
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Loading custom modules")
        self.load_modules()

    def load_modules(self):
        for f in os.listdir(self.folder):
            if not f.endswith('.py'):
                continue
            if f in self.blacklist:
                continue
            base = f.replace('.py', '')
            try:
                command_module = __import__("modules.%s" % base, fromlist=["modules"])
                module = command_module.Module()
                self.modules.append(module)
                self.logger.info("Enabled module: %s" % f)
            except ImportError,e:
                self.logger.warning("Error importing module:%s %s" % (f, e.message))
            except Exception, e:
                self.logger.warning("Error loading module:%s %s" % (f, e.message))

    def run_post(self, urltree, headers={}, cookies={}):
        output = []
        for module in self.modules:
            if 'post' in module.module_types:
                if module.input == "urldata":
                    for row in urltree:
                        try:
                            url, data = row
                            self.logger.debug("Running module %s on url: %s" % (module.name, url))
                            results = module.run(url, data, headers, cookies)
                            if results and len(results):
                                for r in results:
                                    output.extend([module.name, r])
                        except Exception, e:
                            self.logger.warning("Error executing module %s on %s %s: %s" % (module.name, url, data, e.message))
                if module.input == "urls":
                    self.logger.debug("Running module %s on %d urls" % (module.name, len(urltree)))
                    try:
                        results = module.run(urltree, headers, cookies)
                        if results and len(results):
                            for r in results:
                                output.extend([module.name, r])
                    except Exception, e:
                        self.logger.warning("Error executing module %s on urls: %s" % (module.name, e.message))

        return output

    def base_crawler(self, base):
        output = []
        for module in self.modules:
            if module.input == "base" and module.output == "crawler":
                self.logger.debug("Running pre-crawl module %s on base url %s" % (module.name, base))
                results = module.run(base)
                output.extend(results)
        return output
