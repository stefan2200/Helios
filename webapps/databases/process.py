import json
import requests
import re


pages = {
    "Tomcat": "https://www.cvedetails.com/vulnerability-list/vendor_id-45/product_id-887/Apache-Tomcat.html",
    "Struts": "https://www.cvedetails.com/vulnerability-list/vendor_id-45/product_id-6117/Apache-Struts.html",
    "Jboss": "https://www.cvedetails.com/vulnerability-list/vendor_id-1845/Jboss.html"
}

pool = {

}

vuln_versions = {

}


def parse_cve(name, text):
    seen = []
    for cve in re.findall(r'(CVE-\d+-\d+) security vulnerability details', text):
        seen.append(cve)

    if name in pool:
        pool[name].extend(seen)
    else:
        pool[name] = seen
    return seen


def get_versions(name, cve):
    if name not in vuln_versions:
        vuln_versions[name] = {}
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
    vuln_versions[name][cve] = versions
    return versions


def get_cve_pages(name):
    start_url = pages[name]
    url = start_url
    while 1:
        result = requests.get(url)
        found = parse_cve(name, result.text)
        print("Found %d new CVE entries on page" % len(found))
        nextpage = re.search(r'\(This Page\)\s*<a.+?href="(.+?)"', result.text)
        if nextpage:
            url = "https://www.cvedetails.com%s" % nextpage.group(1)
            print("Nextpage: %s" % url)
        else:
            break


def run():
    for name in pages:
        get_cve_pages(name)
        for item in pool[name]:
            vs = get_versions(name, item)
            print("%d vuln versions of %s for %s" % (len(vs), name, item))

    with open('tomcat_vulns.json', 'w') as output:
        output.write(json.dumps(vuln_versions))


run()
