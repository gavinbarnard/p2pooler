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
from util.config import cli_options, parse_config

config_options =  parse_config(cli_options())
r = redis.Redis(port=config_options['redis_port'])

def main():
    dump_me = []
    resp = r.keys("s_*")
    for key in resp:
        dk = r.json().get(key)
        dump_me.append({str(key, 'utf-8'): dk})
    with open("shares.json", 'w') as fh:
        fh.write(json.dumps(dump_me, indent=True))
    
    dump_me = []
    resp = r.keys("b_*")
    for key in resp:
        dk = int(r.get(key))
        dump_me.append({str(key, 'utf-8'): dk})
    with open("balances.json", 'w') as fh:
        fh.write(json.dumps(dump_me, indent=True))
    
    dump_me = []
    resp = r.keys("B_*")
    for key in resp:
        dk = r.json().get(key)
        dump_me.append({str(key, 'utf-8'): dk})
    with open("blocks.json", 'w') as fh:
        fh.write(json.dumps(dump_me, indent=True))

if __name__ == "__main__":
    main()