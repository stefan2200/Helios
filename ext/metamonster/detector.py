import requests


class PassiveDetector:
    url = None
    linux_types = ['debian', 'ubuntu', 'centos', 'fedora', 'red hat']

    def __init__(self, url):
        self.url = url

    def get_page(self):
        result = requests.get(self.url, verify=False)
        return result

    def detect(self, result):
        tech = []
        os = None
        if 'wp-content' in result.text:
            tech.append('wordpress')
            tech.append('php')

        if 'content="drupa' in result.text.lower():
            tech.append('drupal')
            tech.append('php')

        if 'Server' in result.headers:
            for linux_type in self.linux_types:
                if linux_type in result.headers['Server'].lower():
                    os = "linux"

            if 'apache' in result.headers['Server'].lower():
                tech.append('apache')
                if 'win' in result.headers['Server'].lower():
                    os = "windows"

            if 'iis' in result.headers['Server'].lower():
                tech.append('iis')
                os = "windows"

            if 'nginx' in result.headers['Server'].lower():
                tech.append('nginx')

            if 'tomcat' in result.headers['Server'].lower():
                tech.append('tomcat')

            if 'jboss' in result.headers['Server'].lower():
                tech.append('jboss')
        return os, tech

