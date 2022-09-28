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

import redis
import json
from math import floor
from time import time

r = redis.Redis()

start = int(time() * 1000)


def determine_hr(shares, start_time):
    buckets = {
        120: 0,
        300: 0,
        600: 0,
        1800: 0,
        3600: 0,
        7200: 0,
        21600: 0,
        64800: 0
    }
    hr = {}
    for i in reversed(range(len(shares))):
        tdiff = (start_time - shares[i]['timestamp'])/1000
        for k in buckets.keys():
            if tdiff < k:
                buckets[k] += shares[i]['diff']
    for k in buckets.keys():
        hr[k] = floor(buckets[k]/k)
    return hr

def get_shares(user):
    shares = None
    resp = r.keys("s_{}".format(user))
    for key in resp:
        shares = r.json().get(key)
    return shares

def main():
    keys = r.keys("s_*")
    super_overall_hr = {
        120: 0,
        300: 0,
        600: 0,
        1800: 0,
        3600: 0,
        7200: 0,
        21600: 0,
        64800: 0
    }        
    for key in keys:
        userkey = str(key[2:], 'utf-8')
        print("{}\n".format(userkey))
        shares = get_shares(userkey)
        overall_hr = determine_hr(shares, start)
        for k in overall_hr.keys():
            super_overall_hr[k] += overall_hr[k]
        print(json.dumps(overall_hr, indent=True))
    print("Superoverall\n")
    print(json.dumps(super_overall_hr, indent=True))

if __name__ == "__main__":
    main()
