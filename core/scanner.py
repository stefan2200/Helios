from concurrent.futures import ThreadPoolExecutor
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty
import copy
import logging
import sys
import time

class Scanner:
    queue = None
    pool = None
    results = []
    thread_count = 10
    script_engine = None
    # bad idea since results are in list form
    copy_engine = False
    done = 0

    # multi-threading script engine
    def __init__(self, thread_count=None, script_engine=None, logger=logging.INFO):
        if thread_count:
            self.thread_count = thread_count
        self.script_engine = script_engine
        self.logger = logging.getLogger("Scanner")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.debug("Starting Scanner")
        self.queue = Queue()

    def run_scripts(self, request_object):
        scanner = None
        if self.copy_engine:
            scanner = copy.copy(self.script_engine)
        else:
            scanner = self.script_engine
        try:
            scanner.run_scripts(request_object)
        except Exception as e:
            self.logger.warning("Script error %s" % str(e))
        self.done += 1

    def run(self):
        self.pool = ThreadPoolExecutor(max_workers=self.thread_count)
        while True:
            try:
                request = self.queue.get(timeout=1)
                self.logger.debug("Running scripts on %s" % request.url)
                self.pool.submit(self.run_scripts, request)
            except Empty:
                break
            except Exception as e:
                self.logger.warning("Error: %s" % str(e))
                continue
            self.logger.debug("Todo: {0} Done: {1}".format(self.queue.qsize(), self.done))

        time.sleep(5)
