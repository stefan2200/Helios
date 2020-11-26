try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus


class Base:
    module_types = []
    name = ""
    active = True
    # if module can send requests
    request = None
    should_run = True
    input = ""
    output = ""
    severity = 0
    verify = True
    scope = None
    headers = {

    }
    cookies = {

    }

    def run(self, url, data, headers, cookies):
        pass

    def run_passive(self, response):
        pass

    def close(self):
        print("Stopping script")
        self.should_run = False

    def get_params_from_url(self, url):
        if "?" not in url:
            return url, {}
        base, params = url.split('?')
        out = {}
        for sub in params.split('&'):
            parts = sub.split('=')
            if len(sub) > 1:
                out[parts[0]] = parts[1]
            else:
                out[parts[0]] = ""
        return base, out

    def params_to_url(self, base, params):
        out = []
        for key in params:
            out.append("%s=%s" % (quote_plus(key), quote_plus(params[key])))
        return base + "?" +"&".join(out)
