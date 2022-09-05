def cookiecutter(http_cookie, cookie_name=None):
    cookies = http_cookie.split(";")
    response = {}
    for cookie in cookies:
        try:
            cname, cvalue = cookie.split("=")
            cname = cname.strip()
        except Exception as e:
            return None
        if cookie_name:
            if isinstance(cookie_name, str):
                if cookie_name == cname:
                    return cvalue
            elif isinstance(cookie_name, list):
                if cname in cookie_name:
                    response[cname] = cvalue
        else:
            response[cname] = cvalue
    return response