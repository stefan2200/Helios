import logging
import requests
import msgpack
import sys
from time import sleep

class Client:
    ssl = True
    endpoint = None
    username = ""
    password = ""

    token = None
    is_working = False

    def __init__(self, endpoint, username="msf", password="metasploit", use_ssl=True, log_level=logging.INFO):
        self.endpoint = endpoint
        self.username = username
        self.password = password
        self.ssl = use_ssl
        self.logger = logging.getLogger("MetaMonster")
        self.logger.setLevel(log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(ch)
        self.logger.setLevel(log_level)
        self.log_level = log_level
        if self.ssl:
            requests.packages.urllib3.disable_warnings()

    def send(self, method, data=[], is_second_attempt=False):
        try:
            headers = {"Content-type": "binary/message-pack"}
            if method != "auth.login" and self.token:
                data.insert(0, self.token)
            data.insert(0, method)
            result = requests.post(self.endpoint, data=self.encode(data), verify=False, headers=headers)
            decoded = self.decode(result.content)
            return decoded
        except requests.ConnectionError as e:
            self.logger.warning("Cannot connect to endpoint %s. %s" % (self.endpoint, str(e)))
            if is_second_attempt:
                self.logger.error("Second connection attempt failed. cannot connect to endpoint %s" % self.endpoint)
                self.is_working = False
                return None
            else:
                self.logger.info("Retrying in 10 seconds")
                sleep(10)
                return self.send(method, data, True)

        except requests.Timeout as e:
            self.logger.warning("Timeout connecting to endpoint %s." % self.endpoint)
            if is_second_attempt:
                self.logger.error("Second connection attempt failed. cannot connect to endpoint %s" % self.endpoint)
                self.is_working = False
                return None
            else:
                self.logger.info("Retrying in 10 seconds")
                sleep(10)
                return self.send(method, data, True)
        except Exception:
            self.logger.error("Uncaught error %s" % self.endpoint)
            self.is_working = False
            return None

    def encode(self, data):
        return msgpack.packb(data)

    def decode(self, data):
        return msgpack.unpackb(data)

    def auth(self):
        self.logger.debug("Authenticating...")
        res = self.send('auth.login', [self.username, self.password])
        if not res:
            return False

        if b'token' in res:
            self.logger.debug("Authentication successful")
            self.token = res[b'token'].decode()
            self.is_working = True
            return True
        else:
            self.logger.warning("Incorrect credentials for msfrpcd, cannot start")
            self.is_working = False
            return False

    def request(self, action, data=[]):
        if not self.token:
            self.auth()
        if self.is_working:
            return self.send(action, data)
        return None
