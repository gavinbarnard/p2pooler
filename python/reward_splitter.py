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
from util.rpc import wallet_get_transfers_in
from math import floor
from time import time


config_options =  parse_config(cli_options())
r = redis.Redis(port=config_options['redis_port'])

def main():
    in_tx = wallet_get_transfers_in(config_options['wallet_rpc'])
    skeys = r.keys("s_*")
    for tx in in_tx:
        if tx['type'] == "block" and not tx['locked']:
            print("Height: {}\t ts: {}\t reward: {}".format(
                tx['height'],
                tx['timestamp'],
                tx['amount']
            ))
            block_key = str("B_{}".format(tx['height']))
            print("block key: {}".format(block_key))
            block = r.json().get(block_key)
            if not block:
                ts_cmp = tx['timestamp'] * 1000
                all_value = 0
                all_value_dict = {}
                for key in skeys:
                    total_value = 0
                    shares = r.json().get(key)
                    notified = [0,0,0,0,0,0]
                    for share in shares:
                        tdiff = ts_cmp - share['timestamp']
                        if share['timestamp'] < ts_cmp and tdiff < 2.16e7:
                            total_value += share['diff']
                        for i in range(6):
                            if notified[i] == 0:
                                if tdiff > 3.6e6 * i and tdiff < 3.6e6 * (i+1):
                                    notified[i] = 1
                                    print("Found shares in {} hour for {}".format(i, key) )

                    all_value += total_value
                    all_value_dict[str(key[2:], 'utf-8')] = total_value
                all_reward = 0
                all_reward_dict = {}
                for key in all_value_dict.keys():
                    percent = all_value_dict[key] / all_value
                    reward = floor(percent * tx['amount'])
                    all_reward_dict[key] = reward
                    print("{} cumaltive share diff is {} and is worth {} and will get reward {}".format(key, all_value_dict[key], round(percent, 2), reward))
                    all_reward += reward
                print("cumaltive total diff: {}".format(all_value))

                if all_reward > tx['amount']:
                    print("over reward check your maff")
                    raise("Over reward")
                elif all_reward < tx['amount']:
                    print("under reward definetly lost to floor() {}".format(tx['amount'] - all_reward))
                elif all_reward == tx['amount']:
                    print("perfection")
                for key in all_reward_dict.keys():
                    new_key = "b_{}".format(key)
                    cur_value = r.get(new_key)
                    if cur_value:
                        cur_value = int(cur_value)
                        n_value = cur_value + all_reward_dict[key]
                        r.set(new_key, n_value)
                        print("prior balance {} + reward {} = {} for {}".format(cur_value, all_reward_dict[key], n_value, new_key))
                    else:
                        r.set(new_key, all_reward_dict[key])
                        print("new balance reward {} for {}".format(all_reward_dict[key], new_key))
                all_reward_dict['timestamp'] = int(time()*1000)
                resp = r.json().set(block_key, "$", all_reward_dict)
                if resp:
                    print("stored block payout data for block {}".format(tx['height']))
            else:
                print("Already split this block")
                reward = 0
                if "timestamp" in block.keys():
                    print("timestamp: {}".format(block['timestamp']))
                for payee in block.keys():
                    if payee != "timestamp":
                        print("{} allocated {}".format(payee, block[payee]))
                        reward += block[payee]
                print("reward:\t{}".format(reward))
                print("block:\t{}".format(tx['amount']))
                if reward > tx['amount']:
                    print("over reward recorded!!")
                elif reward < tx['amount']:
                    print("under reward floor got {}".format(tx['amount'] - reward))
                elif reward == tx['amount']:
                    print("perfection")

if __name__ == "__main__":
    main()