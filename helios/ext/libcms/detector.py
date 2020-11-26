# cms-detector.py v0.1 / https://github.com/robwillisinfo/cms-detector.py
# edit by stefan2200
import requests


# because I am too lazy to replace all the if statements
class InvalidRequestObject:
    status_code = 404
    text = ""


class CMSDetector:
    headers = {}
    cookies = {}

    def __init__(self, user_agent=None, headers={}, cookies={}):
        self.headers = headers
        self.cookies = cookies
        if user_agent:
            self.headers['User-Agent'] = user_agent

    def get(self, url):
        try:
            return requests.get(url, allow_redirects=False, headers=self.headers, cookies=self.cookies)
        except:
            return InvalidRequestObject()

    def scan_sub(self, base, path):
        if base.endswith('/'):
            base = base[:-1]
        url = "%s/%s/" % (base, path)
        result = self.get(url)
        # 2xx
        if result.status_code != 404 and "not found" not in result.text.lower():
            return self.scan(url)
        return None

    def scan(self, base):
        if base.endswith('/'):
            base = base[:-1]
        wpLoginCheck = self.get(base + '/wp-login.php')
        if wpLoginCheck.status_code == 200 and "user_login" in wpLoginCheck.text and "404" not in wpLoginCheck.text:
            return "wordpress"
        wpAdminCheck = self.get(base + '/wp-admin')
        if wpAdminCheck.status_code == 200 and "user_login" in wpAdminCheck.text and "404" not in wpLoginCheck.text:
            return "wordpress"
        wpAdminUpgradeCheck = self.get(base + '/wp-admin/upgrade.php')
        if wpAdminUpgradeCheck.status_code == 200 and "404" not in wpAdminUpgradeCheck.text:
            return "wordpress"
        wpAdminReadMeCheck = self.get(base + '/readme.html')
        if wpAdminReadMeCheck.status_code == 200 and "404" not in wpAdminReadMeCheck.text:
            return "wordpress"

        ####################################################
        # Joomla Scans
        ####################################################

        joomlaAdminCheck = self.get(base + '/administrator/')
        if joomlaAdminCheck.status_code == 200 and "mod-login-username" in joomlaAdminCheck.text and "404" not in joomlaAdminCheck.text:
            return "joomla"

        joomlaReadMeCheck = self.get(base + '/readme.txt')
        if joomlaReadMeCheck.status_code == 200 and "joomla" in joomlaReadMeCheck.text and "404" not in joomlaReadMeCheck.text:
            return "joomla"

        joomlaTagCheck = self.get(base)
        if joomlaTagCheck.status_code == 200 and 'name="generator" content="Joomla' in joomlaTagCheck.text and "404" not in joomlaTagCheck.text:
            return "joomla"

        joomlaStringCheck = self.get(base)
        if joomlaStringCheck.status_code == 200 and "joomla" in joomlaStringCheck.text and "404" not in joomlaStringCheck.text:
            return "joomla"

        joomlaDirCheck = self.get(base + '/media/com_joomlaupdate/')
        if joomlaDirCheck.status_code == 403 and "404" not in joomlaDirCheck.text:
            return "joomla"

        ####################################################
        # Magento Scans
        ####################################################

        magentoAdminCheck = self.get(base + '/index.php/admin/')
        if magentoAdminCheck.status_code == 200 and 'login' in magentoAdminCheck.text and 'magento' in magentoAdminCheck.text and "404" not in magentoAdminCheck.text:
            return "magento"

        magentoRelNotesCheck = self.get(base + '/RELEASE_NOTES.txt')
        if magentoRelNotesCheck.status_code == 200 and 'magento' in magentoRelNotesCheck.text:
            return "magento"

        magentoCookieCheck = self.get(base + '/js/mage/cookies.js')
        if magentoCookieCheck.status_code == 200 and "404" not in magentoCookieCheck.text:
            return "magento"

        magStringCheck = self.get(base + '/index.php')
        if magStringCheck.status_code == 200 and '/mage/' in magStringCheck.text or 'magento' in magStringCheck.text:
            return "magento"

        magentoStylesCSSCheck = self.get(base + '/skin/frontend/default/default/css/styles.css')
        if magentoStylesCSSCheck.status_code == 200 and "404" not in magentoStylesCSSCheck.text:
            return "magento"

        mag404Check = self.get(base + '/errors/design.xml')
        if mag404Check.status_code == 200 and "magento" in mag404Check.text:
            return "magento"

        ####################################################
        # Drupal Scans
        ####################################################

        drupalReadMeCheck = self.get(base + '/readme.txt')
        if drupalReadMeCheck.status_code == 200 and 'drupal' in drupalReadMeCheck.text and '404' not in drupalReadMeCheck.text:
            return "drupal"

        drupalTagCheck = self.get(base)
        if drupalTagCheck.status_code == 200 and 'name="Generator" content="Drupal' in drupalTagCheck.text:
            return "drupal"

        drupalCopyrightCheck = self.get(base + '/core/COPYRIGHT.txt')
        if drupalCopyrightCheck.status_code == 200 and 'Drupal' in drupalCopyrightCheck.text and '404' not in drupalCopyrightCheck.text:
            return "drupal"

        drupalReadme2Check = self.get(base + '/modules/README.txt')
        if drupalReadme2Check.status_code == 200 and 'drupal' in drupalReadme2Check.text and '404' not in drupalReadme2Check.text:
            return "drupal"

        drupalStringCheck = self.get(base)
        if drupalStringCheck.status_code == 200 and 'drupal' in drupalStringCheck.text:
            return "drupal"

        return None
