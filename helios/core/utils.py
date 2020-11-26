import copy
import string
import random
try:
    from urllib import quote_plus
except ImportError:
    from urllib.parse import quote_plus


# function to make key => value dict lowercase
def multi_to_lower(old_dict, also_values=False):
    new = {}
    for key in old_dict:
        new[key.lower()] = old_dict[key].lower() if also_values else old_dict[key]
    return new


def random_string(length=5, pool=string.ascii_lowercase):
    return ''.join(random.choice(pool) for i in range(length))


# extract all parameters from a string (url parameters or post data parameters)
def params_from_str(string):
    out = {}
    if "&" in string:
        for param in string.split('&'):
            if "=" in param:
                sub = param.split('=')
                key = sub[0]
                value = sub[1]
                out[key] = value
            else:
                out[param] = ""
    else:
        if "=" in string:
            sub = string.split('=')
            key = sub[0]
            value = sub[1]
            out[key] = value
        else:
            out[string] = ""
    return out


# same as above but the other way around
def params_to_str(params):
    groups = []
    for key in params:
        groups.append("%s=%s" % (quote_plus(key), quote_plus(params[key]) if params[key] else ""))
    return '&'.join(groups)


# checks if a script name already exists in the results object
def has_seen_before(key, results):
    for x in results:
        if x['script'] == key:
            return True
    return False


def aspx_strip_internal(post):
    out = {}
    for name in post:
        value = post[name]
        if not name.startswith("__"):
            out[name] = value
    return out


# generate unique url / post data pairs because we do not care about other variations during scanning
def uniquinize(urls):
    out = []
    seen = []
    for x in urls:
        url, data = copy.copy(x)
        newparams, newdata = copy.copy(x)
        if "?" in url:
            u, p = url.split('?')
            p = p.replace(';', '&')
            params = params_from_str(p)
            params = dict(params)
            for k in params:
                params[k] = ""
            newparams = "%s?%s" % (u, params_to_str(params))
        if newdata:
            newdata = dict(newdata)
            for k in newdata:
                newdata[k] = ""
        payload = [newparams, newdata]
        if payload in seen:
            continue
        seen.append(payload)
        out.append([url, data])
    return out


# create dict from response class
def response_to_dict(response):
    return {
        'request': {
            'url': response.request_object.url,
            'data': response.request_object.data,
            'headers': dict(response.request_object.request_headers),
            'cookies': dict(response.request_object.response.cookies)
        },
        'response': {
            'code': response.code,
            'headers': dict(response.headers),
            'content-type': response.content_type
        }
    }


# same but for requests response
def requests_response_to_dict(response):
    return {
        'request': {
            'url': response.request.url,
            'data': response.request.body,
            'headers': dict(response.request.headers),
            'cookies': dict(response.cookies)
        },
        'response': {
            'code': response.status_code,
            'headers': dict(response.headers),
            'content-type': response.headers['Content-Type'] if 'Content-Type' in response.headers else ""
        }
    }
