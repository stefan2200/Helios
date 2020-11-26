import sys
import os
import re
import json

import cms_scanner

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
        text = self.get(url)
        if text:
            version_check_1 = re.search(r'<meta name="generator" content="wordpress ([\d\.]+)', text.text, re.IGNORECASE)
            if version_check_1:
                self.logger.info("Detected %s version %s on %s trough generator tag" % (self.name, version_check_1.group(1), url))
                return version_check_1.group(1)
        check2_url = urljoin(url, 'wp-admin.php')
        text = self.get(check2_url)
        if text:
            version_check_2 = re.search(r'wp-admin\.min\.css\?ver=([\d\.]+)', text.text, re.IGNORECASE)
            if version_check_2:
                self.logger.info("Detected %s version %s on %s trough admin css" % (self.name, version_check_2.group(1), url))
                return version_check_2.group(1)
        self.logger.warning("Unable to detect %s version on url %s" % (self.name, url))

    def run(self, base):
        self.set_logger()
        self.setup()

        version = self.get_version(base)
        info = self.get_version_info(version)

        disco = self.sub_discovery(base)

        plugins = self.read_plugins()
        plugin_data = {}
        vulns = {}
        self.logger.debug("Checking %s for %d plugins" % (base, len(plugins)))
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

    def get_version_info(self, version):
        data = ""
        with open(self.cache_file(self.version_cache_file), 'rb') as f:
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
        try:
            plugins = {}
            with open(self.cache_file(self.plugin_cache_file), 'rb') as f:
                data = f.read().strip()
            json_data = json.loads(data)
            for x in json_data:
                if json_data[x]['popular'] or self.aggressive:
                    plugins[x] = json_data[x]
            return plugins
        except Exception as e:
            self.logger.error("Error reading database file, cannot init plugin database: %s" % str(e))
            return {}

    def get_plugin_version(self, base, plugin):
        plugin_readme_url = urljoin(base, 'wp-content/plugins/%s/readme.txt' % plugin)
        get_result = self.get(plugin_readme_url)
        if get_result and get_result.status_code == 200:
            self.logger.debug("Plugin %s exists, getting version from readme.txt" % plugin)
            text = get_result.text
            get_version = re.search(r'(?s)changelog.+?(\d+\.\d+(?:\.\d+)?)', text, re.IGNORECASE)
            if get_version:
                return get_version.group(1)
        return None

    def update(self):
        try:
            self.logger.info("Updating plugin files")
            data1 = self.get(self.plugin_update_url)
            with open(self.cache_file(self.plugin_cache_file), 'wb') as f:
                x = data1.content
                f.write(x)
            self.logger.info("Updating version files")
            data2 = self.get(self.version_update_url)
            with open(self.cache_file(self.version_cache_file), 'wb') as f:
                x = data2.content
                f.write(x)
            self.logger.info("Update complete")
        except Exception as e:
            self.logger.error("Error updating databases: %s" % str(e))
        return
