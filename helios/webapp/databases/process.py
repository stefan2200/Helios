import json
import requests
import re
import logging
import os


# some code to spider CVE entries (+ vulnerable versions) from cvedetails.com
class CVEProcessor:
    pool = {

    }

    vuln_versions = {

    }
    logger = logging.getLogger("Updater")

    def parse_cve(self, name, text):
        seen = []
        for cve in re.findall(r'(CVE-\d+-\d+) security vulnerability details', text):
            seen.append(cve)

        if name in self.pool:
            self.pool[name].extend(seen)
        else:
            self.pool[name] = seen
        return seen

    def get_versions(self, name, cve):
        if name not in self.vuln_versions:
            self.vuln_versions[name] = {}
        url = "https://www.cvedetails.com/cve/%s/" % cve
        result = requests.get(url)
        text = result.text
        splitter = text.split('<table class="listtable" id="vulnprodstable">')[1]
        splitter = splitter.split('</table>')[0]
        versions = []
        for x in re.findall(r'(?s)(<tr.+?</tr>)', splitter)[1:]:
            version = re.findall(r'(?s)<td>(.+?)</td>', x)[3].strip()
            if version not in versions:
                versions.append(version)
        self.vuln_versions[name][cve] = versions
        return versions

    def get_cve_pages(self, name, start_url):
        url = start_url
        while 1:
            result = requests.get(url)
            found = self.parse_cve(name, result.text)
            self.logger.debug("Found %d new CVE entries on page" % len(found))
            next_page = re.search(r'\(This Page\)\s*<a.+?href="(.+?)"', result.text)
            if next_page:
                url = "https://www.cvedetails.com%s" % next_page.group(1)
                self.logger.debug("Next page: %s" % url)
            else:
                break

    def run(self, entries, output):
        for name in entries:
            self.get_cve_pages(name, entries[name])
            for item in self.pool[name]:
                vs = self.get_versions(name, item)
                self.logger.debug("%d vuln versions of %s for %s" % (len(vs), name, item))
        output_file = '%s_vulns.json' % output
        with open(os.path.join(os.path.dirname(__file__), output_file), 'w') as f:
            self.logger.info("Writing CVE/Version combo to output file %s" % output)
            f.write(json.dumps(self.vuln_versions))
