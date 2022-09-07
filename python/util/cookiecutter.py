#!/usr/bin/env python
# * p2pooler
# * Copyright 2022      grb         <https://github.com/gavinbarnard>
# *
# *   This program is free software: you can redistribute it and/or modify
# *   it under the terms of the GNU General Public License as published by
# *   the Free Software Foundation, either version 3 of the License, or
# *   (at your option) any later version.
# *
# *   This program is distributed in the hope that it will be useful,
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *   GNU General Public License for more details.
# *
# *   You should have received a copy of the GNU General Public License
# *   along with this program. If not, see <http://www.gnu.org/licenses/>.
# */

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