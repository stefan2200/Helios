import os
import logging
import sys


class WebAppModuleLoader:
    folder = ""
    blacklist = ['base_app.py', '__init__.py']
    modules = []
    logger = None
    is_aggressive = False
    module = None

    def __init__(self, folder='../webapp', blacklist=[], is_aggressive=False, log_level=logging.INFO):
        folder = os.path.join(os.path.dirname(__file__), '..', 'webapp')
        self.blacklist.extend(blacklist)
        self.folder = os.path.join(os.path.dirname(__file__), folder)
        self.logger = logging.getLogger("Web App Scanner")
        self.logger.setLevel(log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Loading WebApp scripts from %s" % self.folder )
        self.is_aggressive = is_aggressive

    def load(self, script):
        sys.path.insert(0, os.path.dirname(__file__))
        base = script.replace('.py', '')
        try:
            command_module = __import__("helios.webapp.%s" % base, fromlist=["helios.webapp"])
            module = command_module.Scanner()
            module.logger = self.logger
            module.logger.setLevel(self.logger.getEffectiveLevel())
            self.modules.append(module)

        except ImportError as e:
            self.logger.warning("Error importing script:%s %s" % (base, str(e)))
        except Exception as e:
            self.logger.warning("Error loading script:%s %s" % (base, str(e)))

    def load_modules(self):
        for f in os.listdir(self.folder):
            if not f.endswith('.py'):
                continue
            if f in self.blacklist:
                continue
            self.load(f)

    def run_scripts(self, base, headers={}, cookies={}, scope=None):
        results = {}
        for module in self.modules:
            module.cookies = cookies
            module.scope = scope
            module.run(base)
            results[module.name] = module.results
        return results
