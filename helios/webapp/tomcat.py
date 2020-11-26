from helios.webapp import base_app
import re
import random
import json


# This script detects vulnerabilities in the following Java based products:
# - Tomcat
# - JBoss
class Scanner(base_app.BaseAPP):

    def __init__(self):
        self.name = "Tomcat"
        self.types = []

    def detect(self, url):
        result = self.send(url)
        if not result:
            return False

        rand_val = random.randint(9999, 999999)
        invalid_url = url + "a_%d.jsp" % rand_val if url.endswith('/') else url + "/a_%d.jsp" % rand_val
        invalid_result = self.send(invalid_url)
        if invalid_result and 'Tomcat' in invalid_result.text:
            self.logger.debug("Discovered Tomcat through 404 page")
            return True

        if 'Server' in result.headers:
            if 'Tomcat' in result.headers['Server']:
                self.logger.debug("Discovered Tomcat through Server header")
                return True
            if 'Coyote' in result.headers['Server']:
                self.logger.debug("Discovered Coyote through Server header")
                return True
            if 'JBoss' in result.headers['Server']:
                self.logger.debug("Discovered JBoss through Server header")
                return True
            if 'Servlet' in result.headers['Server']:
                self.logger.debug("Discovered Servlet through Server header")
                return True

        text = result.text

        for link in re.findall('<a.+?href="(.+?)"', text):
            linkdata = link.split('?')[0]
            if linkdata and len(linkdata):
                if not linkdata.startswith('http'):
                    if linkdata.endswith('.do'):
                        self.logger.debug("Discovered Java based app (links end with .do)")
                        return True
                    if linkdata.endswith('.jsp'):
                        self.logger.debug("Discovered Tomcat based app (links end with .jsp)")
                        return True

    def test(self, url):
        db = self.get_db("tomcat_vulns.json")
        data = json.loads(db)

        version_tomcat = self.get_version_tomcat(url)
        if version_tomcat:
            self.logger.info("Tomcat version %s was identified on URL %s" % (version_tomcat, url))
            tomcat_vulns = data['Tomcat']
            self.match_versions(tomcat_vulns, version_tomcat, url)

        version_jboss = self.get_version_jboss(url)
        if version_jboss:
            self.logger.info("Jboss version %s was identified on URL %s" % (version_jboss, url))
            jboss_vulns = data['Jboss']
            self.match_versions(jboss_vulns, version_jboss, url)

    def get_version_tomcat(self, url):
        rand_val = random.randint(9999, 999999)
        invalid_url = url + "a_%d.jsp" % rand_val if url.endswith('/') else url + "/a_%d.jsp" % rand_val
        invalid_result = self.send(invalid_url)
        if 'Tomcat' in invalid_result.text:
            version = re.search('<h3>Apache Tomcat/(.+?)</h3>', invalid_result.text)
            if version:
                return version.group(1)
        return False

    def get_version_jboss(self, url):
        rand_val = random.randint(9999, 999999)
        invalid_url = url + "a_%d.jsp" % rand_val if url.endswith('/') else url + "/a_%d.jsp" % rand_val
        invalid_result = self.send(invalid_url)
        if 'JBoss' in invalid_result.text:
            version = re.search('<h3>JBoss(?:Web)?/(.+?)</h3>', invalid_result.text)
            if version:
                return version.group(1)
        return False


