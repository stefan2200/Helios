from helios.core.utils import params_to_str


class Raw:
    headers = {}
    text = ""
    code = None
    cookies = None
    final_url = None
    content_type = None

    request_object = None

    def __init__(self, text, code, headers, cookies, object, final_url, ctype):
        self.headers = headers
        self.code = code
        self.cookies = cookies
        self.request_object = object
        self.text = text
        self.final_url = final_url
        self.content_type = ctype

    def to_string(self):
        outstr = "[%d] %s %s type:%s (%d bytes)" % (self.code,
                                                    self.request_object.url,
                                                    params_to_str(self.request_object.data) if self.request_object.data else "",
                                                    self.content_type,
                                                    len(self.text))
        return outstr
