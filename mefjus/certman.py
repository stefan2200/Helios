import subprocess
import os
import sys
import logging
import time


class certman:
    cert_dir = ""
    logger = logging.getLogger("Certificate Manager")
    ca = 'CA'
    cert = "mefjus.pem"
    key = "mefjus.pem.key"
    open_ssl_path = '"C:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe"'

    def __init__(self, cert_dir="certs"):
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.debug("Starting CertMan")
        self.cert_dir = cert_dir
        if not os.path.exists(self.cert_dir):
            self.logger.info("Creating certificate directory: %s" % self.cert_dir)
            os.mkdir(self.cert_dir)
        self.test_ssc()

    def test_ssc(self):
        if os.path.exists(os.path.join(self.cert_dir, self.key)) and os.path.exists(os.path.join(self.cert_dir, self.cert)):
            return True
        self.logger.info("Creating self signed certificate")
        self.create_ssc()

    def create_ssc(self):
        self.logger.info("Creating Self-Signed Certificate [1/2]")
        p = self.open_ssl_path if self.open_ssl_path else 'openssl'
        command = p + " req -x509 -nodes -newkey rsa:2048 -keyout %s -out %s -days 365 -subj \"/C=GB/ST=London/L=London/O=Global Security/OU=IT Department/CN=example.com\"" % \
                  (os.path.join(self.cert_dir, self.key), os.path.join(self.cert_dir, self.cert))
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        proc.communicate()
        self.logger.info("Creating Self-Signed Certificate [2/2]")
        if not os.path.exists(os.path.join(self.cert_dir, self.key)):
            self.logger.info("Create PEM KEY fail, is OPENSSL working OK?")

        if not os.path.exists(os.path.join(self.cert_dir, self.cert)):
            self.logger.info("Create PEM fail, is OPENSSL working OK?")
