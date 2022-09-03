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

import socketserver
import redis
import json
from validator import validate_address

r = redis.Redis()

class PPLNS_handler(socketserver.DatagramRequestHandler):
    def handle(self):
        datagram = str(self.rfile.readline().strip(), 'utf-8')
        data_dict = json.loads(datagram)
        check_d = ['user','ts','diff']
        for d in check_d:
            if d not in data_dict.keys():
                print("missing key {} in message".format(d))
                return
        user = data_dict['user']
        if user.find("+") > 0:
            user, diff = user.split("+")
            #print("split off custom diff {}".format(diff))

        if validate_address(user):
            share_key = "s_{}".format(user)
            my_dict = {
                "timestamp": data_dict['ts'],
                "diff": data_dict['diff']
            }
            try:
                resp = r.json().arrappend(share_key, "$", my_dict)
            except redis.exceptions.ResponseError as e:
                if str(e) == "could not perform this operation on a key that doesn't exist":
                    resp = r.json().set(share_key, "$", [])
                    if resp:
                        resp = r.json().arrappend(share_key, "$", my_dict)
            if not resp:
                print("unable to record share for user {} ts {} diff {}", share_key, data_dict['ts'], data_dict['diff'])
        else:
            print("user {} is not a valid monero address".format(user))

def main():
    ServerAddress = ("127.0.0.1", 6969)
    UDPServerObject = socketserver.ThreadingUDPServer(ServerAddress, PPLNS_handler)
    print("Starting PPLNS receiver on 127.0.0.1:6969 start p2pooler now")
    UDPServerObject.serve_forever()

if __name__ == "__main__":
    main()
