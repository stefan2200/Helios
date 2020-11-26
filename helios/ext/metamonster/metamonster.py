import time
import socket
import os
import helios.ext

try:
    from urlparse import urlparse
    from Queue import Queue, Empty
except ImportError:
    from urllib.parse import urlparse
    from queue import Queue, Empty


class MetaMonster:
    client = None
    host = "127.0.0.1"
    port = 55553
    ssl = True
    endpoint = "/api/"
    username = "msf"
    password = "msf"
    modules = []
    aggressive = True
    should_start = True
    log_level = None
    results = {
        'working': [],
        'launched': [],
        'parameters': {}
    }

    os_types = [
        'windows',
        'unix',
        'linux',
        'bsd',
        'multi'
    ]

    exploit_types = [
        'http',
        'webapp'
    ]

    external = {}

    def __init__(self, log_level):
        self.log_level = log_level

    def connect(self, server):
        url = "http%s://%s:%d%s" % ('s' if self.ssl else '', self.host, self.port, self.endpoint)
        self.client = Client(url, username=self.username, password=self.password, log_level=self.log_level)
        self.client.logger.info("Using %s as metasploit endpoint" % url)
        self.client.ssl = self.ssl
        if not self.client.auth():
            self.client.logger.warning("Cannot start MetaMonster, msfrpcd auth was not successful")
            if self.should_start:
                self.client.logger.warning("Attempting to start msfrpcd")
                command = "msfrpcd -U %s -P %s -a %s -p %d %s" % (
                self.username, self.password, self.host, self.port, "-S" if not self.ssl else "")
                command = command.strip()
                os.system(command)
                time.sleep(10)
                self.client = Client(url, username=self.username, password=self.password)
                if not self.client.auth():
                    self.client = None
            self.client = None
        u = urlparse(server)
        self.external['url'] = server
        self.external['host'] = u.netloc
        self.external['method'] = u.scheme
        self.external['ip'] = None
        self.external['port'] = u.port if u.port else 80 if server.startswith('http:') else 443
        self.external['os'] = None
        self.external['tech'] = []

        self.msf = {
            "settings": {
                "shell_type": "bind_tcp",
                "shell_type_fallback": "bind_",
                "shell_port_start": 49200,
                "shell_port_end": 50000,
                "min_success": ["excellent", "good", "average"],
                "allow_dos": False,
                "gather_basic_info": False,
                "drop_after_successful": True,
                "ignore_SRVHOST": True,
                "ignore_privileged": True
            },
            "parameters": {

            }
        }

    def get_exploits(self):
        if self.client and self.client.is_working:
            data = self.client.request("module.exploits")
            for x in data[b'modules']:
                self.modules.append(x.decode())
            self.client.logger.info("Loaded %d modules for searching" % len(self.modules))

    def get_parameters(self):
        params = {}
        params['VHOST'] = self.external['host']
        params['RHOST'] = self.external['ip']
        params['RHOSTS'] = self.external['ip']
        params['RPORT'] = self.external['port']
        params['SSL'] = True if self.external['method'] == "https" else False
        self.msf['parameters'] = params

    def resolve(self, hostname):
        try:
            ip = socket.gethostbyname(hostname)
            self.external['ip'] = ip
            self.client.logger.debug("%s resolves to %s" % (hostname, ip))
        except:
            self.client.logger.error("Error resolving host %s" % hostname)
            pass

    def search(self, arch_type='', subtype='http', keyword=''):
        exploits = []
        for m in self.modules:
            parts = m.split('/')
            try:
                arch, exp_type, name = parts if len(parts) == 3 else [None].extend(parts)
                if arch == arch_type and exp_type == subtype and keyword in m:
                    exploits.append(m)
            except:
                pass
        return exploits

    def detect(self):
        self.resolve(self.external['host'])
        p = PassiveDetector(self.external['url'])
        result = p.get_page()
        if result:
            os, tech = p.detect(result)
            self.external['os'] = os
            self.external['tech'] = tech

    def key_db(self, keywords):
        if "wordpress" in keywords:
            keywords.append('wp_')
        if "drupal" in keywords:
            keywords.append('drupa')
        if "iis" in keywords:
            keywords.append('asp')
        return keywords

    def run_queries(self, queries):
        exploits = []
        self.client.logger.info("Setting parameters")
        self.get_parameters()
        self.client.logger.info("Preparing exploits")
        for query in queries:
            os, sub, keyword = query
            dataresults = self.search(os, sub, keyword)
            for exploit in dataresults:
                if exploit not in exploits:
                    exploits.append(exploit)
                    self.client.logger.debug("Added exploit %s to the queue. query: %s" % (exploit, ','.join(query)))
        self.client.logger.info("Running %d exploits" % len(exploits))
        executor = MetaExecutor(self, exploits)
        working_exploits = executor.start()

        for working in working_exploits:
            self.results['working'].append(working)

        self.results['launched'] = exploits

        self.results['parameters'] = self.msf['parameters']

    def create_queries(self):
        self.client.logger.debug("Starting query creation")
        os_versions = []
        output = []

        if not self.external['os']:
            os_versions = self.os_types
            self.client.logger.debug("Could not guess OS type, using all available: %s" % ', '.join(os_versions))
        elif self.external['os'] == "linux":
            os_versions = ['linux', 'unix', 'multi']
        elif self.external['os'] == "unix":
            os_versions = ['linux', 'unix', 'multi']
        elif self.external['os'] == "windows":
            os_versions = ['windows', 'multi']
        self.client.logger.info("Using operating systems for search query: %s" % ', '.join(os_versions))
        tech = self.external['tech']
        new_list = self.key_db(tech)
        for i in new_list:
            if i not in tech:
                tech.append(i)

        for keyword in tech:
            for search_type in self.exploit_types:
                for os_version in os_versions:
                    output.append(
                        [os_version, search_type, keyword]
                    )
        return output
