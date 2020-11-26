import random
import requests
import helios.modules.module_base
from helios.core.utils import requests_response_to_dict


class Module(helios.modules.module_base.Base):
    cookies = None
    headers = None

    def __init__(self):
        self.name = "Stored XSS"
        self.injections = {}
        self.module_types = ['injection', 'dangerous']
        self.possibilities = [
            '<script>var a = {injection_value};</script>',
            '<xss>var a = {injection_value};</xss>',
            '<img src="{injection_value}" onerror="" />'
        ]
        self.input = "urls"
        self.output = "vuln"
        self.severity = 3

    def run(self, urls, headers={}, cookies={}):
        self.cookies = cookies
        self.headers = headers
        for url in urls:
            url, data = url
            base, params = self.get_params_from_url(url)
            for u in params:
                self.inject(base, params, data, parameter_get=u)
            if data:
                for u in data:
                    self.inject(base, params, data, parameter_post=u)
        results = []
        for url in urls:
            url, data = url
            result = self.validate(url, data)
            if result:
                results.append(result)
        return results

    def validate(self, url, data):
        base, params = self.get_params_from_url(url)
        result = self.send(base, params, data)
        if result:
            for t in self.injections:
                for p in self.possibilities:
                    payload = p.replace('{injection_value}', str(t))
                    if payload in result.text:
                        return {'request': requests_response_to_dict(self.injections[t]), 'match': requests_response_to_dict(result)}
        return False

    def inject(self, url, params, data=None, parameter_get=None, parameter_post=None):
        if parameter_get:
            tmp = dict(params)
            for injection_value in self.possibilities:
                random_int = random.randint(9999, 9999999)
                payload = injection_value.replace('{injection_value}', str(random_int))
                payload = payload.replace('{original_value}', str(params[parameter_get]))
                tmp[parameter_get] = payload
                result = self.send(url, tmp, data)
                self.injections[str(random_int)] = result

        if parameter_post:
            tmp = dict(data)
            for injection_value in self.possibilities:
                random_int = random.randint(9999, 9999999)
                payload = injection_value.replace('{injection_value}', str(random_int))
                payload = payload.replace('{original_value}', str(data[parameter_post]))
                tmp[parameter_post] = payload
                result = self.send(url, params, tmp)
                self.injections[str(random_int)] = result

    def send(self, url, params, data):
        result = None
        headers = self.headers
        cookies = self.cookies
        try:
            if data:
                result = requests.post(url, params=params, data=data, headers=headers, cookies=cookies)
            else:
                result = requests.get(url, params=params, headers=headers, cookies=cookies)
        except Exception as e:
            print(str(e))
        return result
