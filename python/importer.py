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
from functools import cmp_to_key
from util.config import cli_options, parse_config

config_options =  parse_config(cli_options())
r = redis.Redis(port=config_options['redis_port'])


def ts_sort(a, b):
    if [a['timestamp'] < b['timestamp']]:
        return -1
    elif [a['timestamp'] > b['timestamp']]:
        return 1
    elif [a['timestamp'] == b['timestamp']]:
        return 0


def main():
    with open("shares.json", 'r') as fh:
        dump_truck = json.loads(fh.read())
    redis_keys = r.keys("s_*")
    for val in dump_truck:
        key = list(val.keys())[0]
        bkey = bytes(key, 'utf-8')
        if bkey in redis_keys:
            print("duplicate key")
            redis_value = r.json().get(key)
            merge_value = val[key]
            merged_list = redis_value + merge_value
            duplicate_confidence = 0
            max_range = 0
            if len(redis_value) > len(merge_value):
                max_range = len(merge_value)
            else:
                max_range = len(redis_value)
            for i in range(0, max_range):
                if redis_value[i] == merge_value[i]:
                    duplicate_confidence += 1
                if duplicate_confidence >= 100:
                    break
            if duplicate_confidence >=100:
                print("pretty sure this is duplicate data")
            else:    
                sort_list = sorted(merged_list, key=cmp_to_key(ts_sort))
                print("merging monster")
                print(json.dumps(sort_list, indent=True))
        else:
            #r.json().set(key, "$", val[key])
            print("imported {}".format(key))
    with open("balance.json", 'r') as fh:
        dump_truck = json.loads(fh.read())
    redis_keys = r.keys("b_*")
    for val in dump_truck:
        key = list(val.keys())[0]
        print("key:{} val: {}".format(key, val[key]))
        #r.set(key, val[0])

    with open("blocks.json", 'r') as fh:
        dump_truck = json.loads(fh.read())
    for val in dump_truck:
        key = list(val.keys())[0]
        print("key: {} val: {}".format(key, val[key]))



if __name__ == "__main__":
    main()