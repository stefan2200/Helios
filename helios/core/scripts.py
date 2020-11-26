import os
import json
from helios.core.engine import MatchObject, CustomRequestBuilder, RequestBuilder
from helios.core.utils import has_seen_before, response_to_dict
import sys
import logging
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


class ScriptEngine:
    scripts_active = []
    scripts_fs = []
    scripts_passive = []
    results = []
    triggers = []
    can_fs = True
    can_exploit = True
    s = None
    options = None
    log_level = logging.INFO
    writer = None

    def __init__(self, options=None, logger=logging.INFO, database=None):
        self.logger = self.logger = logging.getLogger("ScriptEngine")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.debug("Starting script parser")
        self.options = options
        self.log_level = logger
        self.parse_scripts()
        self.writer = database

    def parse_scripts(self):
        self.s = ScriptParser(logger=self.log_level)
        self.s.load_scripts()
        self.scripts_active = []
        self.scripts_fs = []
        self.scripts_passive = []

        for script in self.s.scripts:
            matches = []
            if self.options:
                if 'all' not in self.options:
                    if self.options and 'options' in script:
                        for sub in script['options']:
                            if str(sub) not in self.options:
                                self.logger.debug("Disabling script %s because %s is not enabled" % (script['name'], sub))
                                continue
            else:
                if 'options' in script and 'dangerous' in script['options']:
                    self.logger.debug("Disabling script %s because dangerous flag is present, use --options all or add the dangerous flag to override" % (script['name']))
                    continue

            for x in script['matches']:
                mobj = MatchObject(
                    mtype=x['type'],
                    match=x['match'],
                    location=x['location'],
                    name=x['name'] if 'name' in x else script['name'],
                    options=list(x['options'])
                )
                matches.append(mobj)

            script_data = {
                "name": script['name'],
                "find": script['find'],
                "severity": script['severity'],
                "request": script['request'],
                "data": script['data'] if 'data' in script else {},
                "matches": matches
            }
            if not script['request']:
                if script['run_at'] == "response":
                    self.scripts_passive.append(script_data)
                if script['run_at'] == "fs":
                    self.scripts_fs.append(script_data)

            if script['request']:
                self.scripts_active.append(script_data)

    def run_fs(self, base_url):
        links = []
        if self.can_fs:
            for script in self.scripts_fs:
                if str(script['find']) == "once":
                    if has_seen_before(script['name'], self.results):
                        continue
                data = script['data']
                new_req = CustomRequestBuilder(
                    url=data['url'],
                    data=data['data'] if 'data' in data else None,
                    headers=data['headers'] if 'headers' in data else {},
                    options=data['options'] if 'options' in data else [],
                )
                new_req.root_url = base_url
                result = new_req.run()
                if result:
                    # is found so added to crawler
                    if result.response.code == 200:
                        links.append([urlparse.urljoin(base_url, new_req.url), new_req.data])
                    for match in script['matches']:
                        mresult = match.run(result.response)
                        if mresult:
                            res = "%s [%s] > %s" % (script['name'], result.response.to_string(), mresult)
                            self.logger.info("Discovered: %s" % res)
                            if self.writer:
                                severity = script['severity'] if 'severity' in script else 0
                                text = json.dumps({"request": response_to_dict(result.response), "match": mresult})
                                self.writer.put(result_type="Basic Script - Filesystem", script=script['name'], severity=severity, text=text)
                            self.results.append({"script": script['name'], "match": mresult, "data": response_to_dict(result.response)})
            return links

    def run_scripts(self, request):
        for script in self.scripts_passive:
            if str(script['find']) == "once":
                if has_seen_before(script['name'], self.results):
                    continue
            for match in script['matches']:
                result = match.run(request.response)
                if result:
                    res = "%s [%s] > %s" % (script['name'], request.response.to_string(), result)
                    self.logger.info("Discovered: %s" % res)
                    if self.writer:
                        severity = script['severity'] if 'severity' in script else 0
                        text = json.dumps({"request": response_to_dict(request.response), "match": result})
                        self.writer.put(result_type="Basic Script - Passive", script=script['name'],
                                        severity=severity, text=text, allow_only_once=str(script['find']) == "once")
                    self.results.append(
                        {"script": script['name'], "match": result, "data": response_to_dict(request.response)})
        if self.can_exploit:
            for script in self.scripts_active:
                if str(script['find']) == "once":
                    if has_seen_before(script['name'], self.results):
                        continue
                try:
                    r = RequestBuilder(
                        req=request,
                        inject_type=script['request'],
                        inject_value=script['data']['inject_value'],
                        matchobject=script['matches'],
                        name=script['name']
                    )
                    results = []
                    results = r.run()
                    if results:
                        for scan_result in results:
                            if scan_result not in self.results:
                                res = "[%s] URL %s > %s" % (script['name'], scan_result['request']['request']['url'], scan_result['match'])
                                self.logger.info("Discovered: %s" % res)
                                if self.writer:
                                    severity = script['severity'] if 'severity' in script else 0
                                    text = json.dumps(scan_result)
                                    self.writer.put(result_type="Basic Script - Active", script=script['name'],
                                                    severity=severity, text=text)
                                self.results.append(res)
                except Exception as e:
                    self.logger.warning("Error running script %s: %s" % (script['name'], str(e)))


class ScriptParser:
    directory = '../scripts'
    root_dir = ''
    script_dir = ''
    scripts = []
    logger = None

    def __init__(self, newdir=None, logger=logging.INFO):
        self.root_dir = os.path.dirname(os.path.realpath(__file__))
        self.script_dir = os.path.join(self.root_dir, self.directory) if not newdir else newdir
        self.logger = logging.getLogger("ScriptParser")
        self.logger.setLevel(logger)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logger)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        if not os.path.isdir(self.script_dir):
            self.logger.error("Cannot initialise script engine, directory '%s' does not exist" % self.script_dir)
        self.scripts = []

    def load_scripts(self):
        self.logger.debug("Init script engine")
        for f in os.listdir(self.script_dir):
            script = os.path.join(self.script_dir, f)
            if os.path.isfile(script):
                try:
                    with open(script, 'r') as scriptfile:
                        data = scriptfile.read()
                    jsondata = json.loads(data)
                    self.scripts.append(jsondata)
                except ValueError:
                    self.logger.error("Script %s appears to be invalid JSON, ignoring" % f)
                    pass
                except IOError:
                    self.logger.error("Unable to access script file %s, ignoring" % f)
                    pass
        self.logger.info("Script Engine loaded %d scripts" % len(self.scripts))
