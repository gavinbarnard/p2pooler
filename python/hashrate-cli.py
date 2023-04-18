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
from functools import cmp_to_key
from cmd import Cmd
r = redis.Redis()

def hr5_sort(a, b):
    val = "300"
    if a["hr"][val] > b["hr"][val]:
        return 1
    elif b["hr"][val] > a["hr"][val]:
        return -1
    else:
        return 0

def hr10_sort(a, b):
    val = "600"
    if a["hr"][val] > b["hr"][val]:
        return 1
    elif b["hr"][val] > a["hr"][val]:
        return -1
    else:
        return 0

def hr30_sort(a, b):
    val = "1800"
    if a["hr"][val] > b["hr"][val]:
        return 1
    elif b["hr"][val] > a["hr"][val]:
        return -1
    else:
        return 0

def _get_wallets():
    wallet_list = []
    [wallet_list.append(str(key[2:], 'utf-8')) for key in r.keys("h_*")]
    return wallet_list

def _get_all_hr():
    hr = []
    w = _get_wallets()
    for i in w:
        t = r.json().get("h_{}".format(i))
        allz = True
        for x in t.items():
            if x[1] != 0:
                allz = False
        if not allz and i != "super":
            hr.append({"wallet": i, "hr": t})
    return hr


class HashShell(Cmd):
    intro = "Welcome to p2pooler hashshell"
    prompt = "(p2pooler) "
    def get_wallets(self, arg):
        'Get a list of wallets'
        w = _get_wallets()
        [print(i) for i in w]

    def do_top_table_5m(self, arg):
        'Get a list of top hashers in last 5m'
        hr = _get_all_hr()
        hr_s = sorted(hr, key=cmp_to_key(hr5_sort), reverse=True)
        for i in range(5):
            try:
                print(f"Wallet:\t{hr_s[i]['wallet']}\t Hashrate: {hr_s[i]['hr']['300']}")
            except IndexError:
                return

    def do_top_table_10m(self, arg):
        'Get a list of top hashers in last 10m'
        hr = _get_all_hr()
        hr_s = sorted(hr, key=cmp_to_key(hr10_sort), reverse=True)
        for i in range(5):
            try:
                print(f"Wallet:\t{hr_s[i]['wallet']}\t Hashrate: {hr_s[i]['hr']['600']}")
            except IndexError:
                return

    def do_top_table_30m(self, arg):
        'Get a list of top hashers in last 30m'
        hr = _get_all_hr()
        hr_s = sorted(hr, key=cmp_to_key(hr30_sort), reverse=True)
        for i in range(5):
            try:
                print(f"Wallet:\t{hr_s[i]['wallet']}\t Hashrate: {hr_s[i]['hr']['1800']}")
            except IndexError:
                return

    def do_exit(self, arg):
        'Exits the cli'
        return True

    def do_quit(self, arg):
        'Exits the cli'
        return True

if __name__ == "__main__":
    HashShell().cmdloop()