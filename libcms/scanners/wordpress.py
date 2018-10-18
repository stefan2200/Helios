import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import cms_scanner
import re, json
try:
    from urlparse import urljoin, urlparse
except ImportError:
    from urllib.parse import urljoin, urlparse


class Scanner(cms_scanner.Scanner):
    plugin_update_url = "https://data.wpscan.org/plugins.json"
    plugin_cache_file = "wordpress_plugins.json"

    version_update_url = "https://data.wpscan.org/wordpresses.json"
    version_cache_file = "wordpress_versions.json"

    def __init__(self):
        self.name = "wordpress"
        self.update_frequency = 3600 * 48

    def get_version(self, url):
        text = self.get(url).text
        version_check_1 = re.search('<meta name="generator" content="wordpress (\d+\.\d+\.\d+)', text, re.IGNORECASE)
        if version_check_1:
            return version_check_1.group(1)
        check2_url = urljoin(url, 'wp-admin.php')
        result = self.get(check2_url).text
        version_check_2 = re.search('wp-admin\.min\.css\?ver=(\d+\.\d+\.\d+)', result, re.IGNORECASE)
        if version_check_2:
            return version_check_2.group(1)

    def run(self, base):
        self.set_logger()
        self.setup()

        version = self.get_version(base)
        info = self.get_version_info(version)

        disco = self.sub_discovery(base)

        plugins = self.read_plugins()
        plugin_data = {}
        vulns = {}
        for plugin in plugins:
            plugin_version = self.get_plugin_version(base, plugin)
            if plugin_version:
                plugin_data[plugin] = plugin_version
                self.logger.debug("Got %s as version number for plugin %s" % (plugin_version, plugin))
                p_vulns = self.get_vulns(plugin_version, plugins[plugin])
                self.logger.info("Found %d vulns for plugin %s version %s" % (len(p_vulns), plugin, version))
                vulns[plugin] = p_vulns
        return {
            'version': version,
            'plugins': plugin_data,
            'plugin_vulns': vulns,
            'version_vulns': info,
            'discovery': disco
        }

    def get_vulns(self, version, plugin):
        vulns = []
        for vuln in plugin['vulnerabilities']:
            if self.match_versions(version, vuln['fixed_in']):
                vulns.append(vuln)
        return vulns

    def match_versions(self, version, fixed_in):
        if version == fixed_in:
            return False
        parts_version = version.split('.')
        parts_fixed_in = fixed_in.split('.')

        if len(parts_version) <= len(parts_fixed_in):
            for x in range(len(parts_version)):
                if int(parts_version[x]) < int(parts_fixed_in[x]):
                    return True
                if int(parts_version[x]) > int(parts_fixed_in[x]):
                    return False
            return False

        else:
            for x in range(len(parts_fixed_in)):
                if int(parts_version[x]) < int(parts_fixed_in[x]):
                    return True
                if int(parts_version[x]) > int(parts_fixed_in[x]):
                    return False
            return False

    def get_version_info(self, version):
        data = ""
        with open(self.cache_file(self.version_cache_file), 'r') as f:
            data = f.read().strip()
        json_data = json.loads(data)
        if version in json_data:
            return json_data[version]
        return None

    def sub_discovery(self, base):
        logins = []
        get_users = self.get(urljoin(base, 'wp-json/wp/v2/users'))
        if get_users:
            result = json.loads(get_users.text)
            for user in result:
                user_id = user['id']
                name = user['name']
                login = user['slug']
                logins.append({'id': user_id, 'username': login, 'name': name})

        return {'users': logins}

    def read_plugins(self):
        plugins = {}
        with open(self.cache_file(self.plugin_cache_file), 'r') as f:
            data = f.read().strip()
        json_data = json.loads(data)
        for x in json_data:
            if json_data[x]['popular'] or self.aggressive:
                plugins[x] = json_data[x]
        return plugins

    def get_plugin_version(self, base, plugin):
        plugin_readme_url = urljoin(base, 'wp-content/plugins/%s/readme.txt' % plugin)
        get_result = self.get(plugin_readme_url)
        if get_result:
            self.logger.debug("Plugin %s exists, getting version from readme.txt" % plugin)
            text = get_result.text
            get_version = re.search('(?s)changelog.+?(\d+\.\d+(?:\.\d+)?)', text, re.IGNORECASE)
            if get_version:
                return get_version.group(1)
        return None

    def update(self):
        try:
            self.logger.info("Updating plugin files")
            data1 = self.get(self.plugin_update_url)
            with open(self.cache_file(self.plugin_cache_file), 'w') as f:
                x = data1.text.encode('ascii', 'ignore')
                f.write(x)
            self.logger.info("Updating version files")
            data2 = self.get(self.version_update_url)
            with open(self.cache_file(self.version_cache_file), 'w') as f:
                x = data2.text.encode('ascii', 'ignore')
                f.write(x)
            self.logger.info("Update complete")
        except Exception as e:
            self.logger.error("Error updating databases" % str(e))
        return
