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

import requests

def get_summary(rpc_port, token, site="localhost"):
    headers = {}
    headers['Authorization'] = "Bearer {}".format(token)
    r = requests.get("http://{}:{}/1/summary".format(site, rpc_port), headers=headers)
    r.raise_for_status()
    return r.json()

def get_miners(rpc_port, token, site="localhost"):
    headers = {}
    headers['Authorization'] = "Bearer {}".format(token)
    r = requests.get("http://{}:{}/1/miners".format(site, rpc_port), headers=headers)
    r.raise_for_status()
    mf = r.json()['format']
    miners = r.json()['miners']
    user_idx = mf.index("user")
    rig_idx = mf.index("rig_id")
    r_miners = {}
    for m in miners:
        user = m[user_idx]
        rig_id = m[rig_idx]
        if user in r_miners.keys():
            r_miners[user]['rigs'].append(rig_id)
        else:
            r_miners[user] = {}
            r_miners[user]['rigs'] = [rig_id]
    return r_miners

def get_workers(rpc_port, token, site="localhost"):
    headers = {}
    headers['Authorization'] = "Bearer {}".format(token)
    r = requests.get("http://{}:{}/1/workers".format(site, rpc_port), headers=headers)
    r.raise_for_status()
    return r.json()


def get_hr_wallet(rpc_port, token, wallet, site="localhost"):
    miners = get_miners(rpc_port, token, site)
    hr = 0
    if wallet in miners.keys():
        workers = get_workers(rpc_port, token, site)
        for worker in workers['workers']:
            if worker[0] in miners[wallet]['rigs']:
                hr += worker[8]
    return hr * 1000

def get_workers_by_wa(rpc_port, token, wallet, site="localhost"):
    resp = []
    miners = get_miners(rpc_port, token, site)
    if wallet in miners.keys():
        workers = get_workers(rpc_port, token, site)
        for worker in workers['workers']:
            if worker[0] in miners[wallet]['rigs']:
                resp.append(worker)
    return resp