import re
import requests
from Utils import aspx_strip_internal
import json

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

# Notice! this file is purely conceptual and has nothing to do with the rest of the project
# this wrapper detects ASPX post back values and combines it with the supplied post data to send valid requests


class Event:
    url = ""
    inputs = {}
    actions = []
    session = None

    def __init__(self, session):
        self.session = session
        if not self.session:
            self.session = requests.session()

    def run_actions(self):
        for a in self.actions:
            self.run_action(a)

    def run_action(self, action):
        tmp = dict(self.inputs)
        target, argument = action
        internal = aspx_strip_internal(tmp)
        tmp['__EVENTTARGET'] = target
        tmp['__EVENTARGUMENT'] = argument
        print("Submitting action %s:%s" % (target, argument))
        try:
            print("[POST] %s %s" % (self.url, json.dumps(internal)))
            result = self.session.post(self.url, tmp)
            if result:
                print("[%d] %s len:%d type:%s" % (result.status_code, result.url, len(result.text), result.headers['content-type'] if 'content-type' in result.headers else 'Unknown'))
                return result
            return None
        except requests.Timeout:
            print("POST %s resulted in timeout" % self.url)
        except requests.Timeout:
            print("POST %s caused an exception" % self.url)
        return False


class Crawler:
    form_re = re.compile('(?s)(<form.+?</form>)', re.IGNORECASE)
    form_action_re = re.compile('<form.+?action=[\'"](.*?)[\'"]', re.IGNORECASE)
    hidden_re = re.compile('<input(.+?)(?:/)?>', re.IGNORECASE)
    name_re = re.compile('name=[\'"](.+?)[\'"]', re.IGNORECASE)
    type_re = re.compile('type=[\'"](.+?)[\'"]', re.IGNORECASE)
    value_re = re.compile('value=[\'"](.+?)[\'"]', re.IGNORECASE)
    other_types = [
        re.compile('(?s)<(select).+?name=[\'"](.+?)[\'"].+?value=[\'"](.*?)[\'"]', re.IGNORECASE),
        re.compile('(?s)<(textarea).+?name=[\'"](.+?)[\'"].+?>(.*?)</textarea>', re.IGNORECASE)
    ]
    postback_re = re.compile('__doPostBack\(.*?[\'"](.+?)[\'"\\\]\s*,\s*[\'"](.+?)[\'"\\\]', re.IGNORECASE)

    def __init__(self, session, method=""):
        self.session = session
        pass

    def get_inputs(self, url, html):
        data = []
        html = html.replace('&#39;', "'")
        for form in self.form_re.findall(html):
            post_url = url
            get_action = self.form_action_re.search(form)
            if get_action:
                post_url = urlparse.urljoin(url, get_action.group(1))
            handler = Event(self.session)
            handler.url = post_url
            for inp in self.hidden_re.findall(form):
                name = self.name_re.search(inp)
                if not name:
                    continue
                name = name.group(1)
                input_type = self.type_re.search(inp)
                if not input_type:
                    continue
                input_type = input_type.group(1)
                value = self.value_re.search(inp)
                value = value.group(1) if value else ""
                handler.inputs[name]= value
            for match in self.other_types:
                results = match.findall(form)
                for entry in results:
                    handler.inputs[entry[1]] = entry[2]
            for postback in self.postback_re.findall(form):
                if postback not in handler.actions:
                    handler.actions.append(postback)
            data.append(handler)
        return data
