import re
import requests
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import helios.modules.module_base
from helios.core.utils import requests_response_to_dict, random_string
from bs4 import BeautifulSoup


class Module(helios.modules.module_base.Base):

    def __init__(self):
        self.name = "File Uploads"
        self.input = "urls"
        self.injections = {}
        self.module_types = ['discovery']
        self.output = "vulns"
        self.severity = 2
        self.needle = None

    def run(self, urls, headers={}, cookies={}):
        results = []
        self.cookies = cookies
        self.headers = headers
        list_urls = []
        for u in urls:
            if u[0].split('?')[0] not in list_urls:
                list_urls.append(u[0].split('?')[0])

        for f in list_urls:
            working = 0
            result_fp = self.send(f, self.headers, self.cookies)
            if result_fp and self.scope.in_scope(result_fp.url):
                for upl_form in re.findall(r'(?s)(<form.+?multipart/form-data".+?</form>)', result_fp.text):
                    try:
                        post_body = {}
                        soup = BeautifulSoup(upl_form, "lxml")
                        f = soup.find('form')
                        # if form has no action use current url instead
                        action = urlparse.urljoin(result_fp.url, f['action']) if f.has_attr('action') else result_fp.url
                        for frm_input in f.findAll('input'):
                            if frm_input.has_attr('name') and frm_input.has_attr('type'):
                                if frm_input['type'] == "file":
                                    post_body[frm_input['name']] = "{file}"
                                else:
                                    post_body[frm_input['name']] = frm_input['value'] \
                                        if frm_input.has_attr('value') else random_string(8)
                        output, boundry = self.get_multipart_form_data(result_fp.url, post_body)

                        self.headers['Content-Type'] = 'multipart/form-data; boundary=%s' % boundry
                        send_post = self.send(action, params=None, data=output)
                        if send_post and send_post.status_code == 200:
                            result = self.find_needle(action)
                            if result:
                                results.append({'request': requests_response_to_dict(send_post),
                                                "match": "File was successfully uploaded to %s" % result})
                    except:
                        pass

        return results

    def find_needle(self, url):
        if 'Content-Type' in self.headers:
            del self.headers['Content-Type']
        filename, match, contents = self.needle
        common_dirs = ['uploads', 'upload', 'files', 'data', 'images', 'img', 'assets', 'cache']
        root = urlparse.urljoin(url, '/')
        upath = '/'.join(url.split('/')[:-1]) + "/"
        for d in common_dirs:
            if root == url:
                break
            rpath = "%s%s/%s" % (root, d, filename)
            get = self.send(rpath, None, None)
            if get and get.status_code == 200 and match in get.text:
                return rpath
        for d in common_dirs:
            if upath == root:
                continue
            rpath = "%s%d/%s" % (upath, d, filename)
            get = self.send(rpath, None, None)
            if get and get.status_code == 200 and match in get.text:
                return rpath

    def get_multipart_form_data(self, url, post_data):
        output = ""
        boundry = "----WebKitFormBoundary%s" % random_string(15)
        output += "--" + boundry + "\r\n"
        for name in post_data:
            value = post_data[name]
            opt = ''

            if value == "{file}":
                outf = self.generate_file(url)
                self.needle = outf
                filename, match, contents = outf
                name = name + '"; filename="%s' % filename
                value = contents
                opt = 'Content-Type: \r\n'

            header = 'Content-Disposition: form-data; name="%s"\r\n' % name
            header += opt
            header += "\r\n"

            outstr = "%s%s\r\n" % (header,  value)
            output += outstr
            output += "--" + boundry + "\r\n"
        output = output[:-2] + "--"
        return output, boundry.strip()

    def generate_file(self, url):
        filename = "upload.txt"
        match = random_string(8)
        contents = match
        if ".php" in url:
            filename = random_string(8) + ".php"
            match = random_string(8)
            contents = "<?php echo '%s'; ?>" % match

        if ".asp" in url:
            # also catches aspx
            filename = random_string(8) + ".asp"
            match = random_string(8)
            contents = '<%% Response.Write("%s") %%>' % match

        if ".jsp" in url:
            filename = random_string(8) + ".jsp"
            match = random_string(8)
            contents = '<%% out.print("%s"); %%>' % match

        return filename, match, contents

    def send(self, url, params, data):
        result = None
        headers = self.headers
        cookies = self.cookies
        try:
            if data:
                result = requests.post(url, params=params, data=data,
                                       headers=headers, cookies=cookies, verify=self.verify)
            else:
                result = requests.get(url, params=params,
                                      headers=headers, cookies=cookies, verify=self.verify)
        except Exception as e:
            pass
        return result
