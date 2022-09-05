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

import json
import redis
from glob import glob
from math import floor
from datetime import datetime
from pymemcache.client import base
from os.path import exists
from time import time

from util.config import parse_config, cli_options
#from util.moneropooldb import get_mined, get_payments, get_pplns_window_estimate
from util.cookiecutter import cookiecutter
from util.rpc import monerod_get_block, monerod_get_info, wallet_get_transfers_out, wallet_get_transfers_in
from util.p2pool_stats import get_stat
from util.p2pooler import get_summary, get_hr_wallet, get_miners, get_workers_by_wa
#from bonusbot import get_latest_winner

BLOCK_TIME = 120
VERSION_PREFIX = "/1/"
config_items = parse_config(cli_options())
r = redis.Redis(port=config_items['redis_port'])
#pooldd = config_items['pooldd']

def get_shares(wallet=None):
    share_count = 0
    if wallet:
        share_count = r.json().arrlen("s_{}".format(wallet))
    return share_count


def get_stats(wallet=None):
    p2local = get_stat(config_items['p2pool_stats'], "local")
    p2network = get_stat(config_items['p2pool_stats'], "network")
    p2pool = get_stat(config_items['p2pool_stats'], "pool")
    p2stats_mod = get_stat(config_items['p2pool_stats'], "stats_mod")
    info = monerod_get_info(config_items['monero_rpc'])
    p2pooler_sum = get_summary(config_items['p2pooler_rpc'], config_items['p2pooler_token'])
    blocks = get_mined()
    blocks.reverse()
    p2_round = round(p2stats_mod['pool']['roundHashes'] / p2network['difficulty'] * 100, 2)
    miner_hr = 0
    miner_bal = 0
    worker_count = 0
    miner_share = 0
    connected_miners = len(get_miners(config_items['p2pooler_rpc'], config_items['p2pooler_token']))
    if wallet:
        miners = get_miners(config_items['p2pooler_rpc'],config_items['p2pooler_token'])
        if wallet in miners.keys():
            miner_hr = get_hr_wallet(config_items['p2pooler_rpc'],config_items['p2pooler_token'], wallet)
            bal = r.get("b_{}".format(wallet))
            if bal:
                miner_bal = int(bal) / 1e12
            else:
                miner_bal = 0
            worker_count = len(miners[wallet]['rigs'])
            miner_share = get_shares(wallet)
    stat_array = {
        "pool_hashrate": p2local['hashrate_15m'],
        "p2pool_hashrate": p2pool['pool_statistics']['hashRate'],
        "network_hashrate": p2network['difficulty'] / BLOCK_TIME,
        "network_difficulty": p2network['difficulty'],
        "round_hr": "Current effort: {}%<br/>Average Effort: {}%".format(p2local['current_effort'], p2local['average_effort']),
        "p2pool_round": "{}%".format(p2_round),
        "p2pool_reward": p2local['reward'] / 1e12,
        "p2pool_shares": p2local['p2pool_shares'],
        "network_height": info['height'],
        "last_block_found": blocks[0]['height'],
        "pool_blocks_found": len(blocks),
        "payment_threshold": 0.005,
        "pool_fee": 0,
        "pool_port": 4242,
        "pool_ssl_port": 4244,
        "connected_miners": connected_miners,
        "miner_hashrate": miner_hr,
        "miner_balance": miner_bal,
        "miner_share": miner_share,
        "worker_count": worker_count
    }
    return json_generic_response(stat_array)

def get_mined():
    mined_blocks = []
    txs = wallet_get_transfers_in(config_items['wallet_rpc'])
    for tx in txs:
        if tx['type'] == "block":
            mblock = monerod_get_block(config_items['monero_rpc'], tx['height'], config_items['monero_ip'])
            bh = mblock['block_header']
            if tx['locked']:
                status = "LOCKED"
            else:
                status = "UNLOCKED"
            mined_blocks.append({"height": tx['height'],
                    "hash": bh['miner_tx_hash'],
                    "status": status,
                    "difficulty": bh['difficulty'],
                    "breward": bh['reward'],
                    "reward": tx['amount'],
                    "timestamp": bh['timestamp'],
                    "dt": bh['timestamp']})
    return mined_blocks

def data_gif():
    contype = "image/gif"
    gif = ""
    if exists("data.gif"):
        with open("data.gif", 'rb') as fh:
            gif = fh.read()
    return contype, gif

def pool_page():
    contype = "text/html"
    html = ""
    if (exists(config_items['v1_template_html'])):
        with open(config_items['v1_template_html'], 'r') as fh:
            html = fh.read()
        html = html.replace("<!-- SITENAME --!>", config_items['sitename'])
        html = html.replace("<!-- POOL_LOGO --!>", config_items['pool_logo'])
    return contype, html

def block_page(block):
    contype = "text/html"
    html = ""
    block_data = "<table>"
    monero_block = monerod_get_block(config_items['monero_rpc'], block, config_items['monero_ip'])
    for k in monero_block.keys():
        if k == "block_header":
            block_data = block_data + "<tr><td>block_header</td><td><table>"
            for bd in monero_block[k].keys():
                block_data = block_data + "<tr><td>{}</td><td>{}</td></tr>".format(bd,json.dumps(monero_block[k][bd], indent=True))
            block_data = block_data + "</table></td></tr>"
        elif k == "json":
            block_data = block_data + "<tr><td>json</td><td><table>"
            bd_json = json.loads(monero_block[k])
            for bd in bd_json.keys():
                if bd == "miner_tx":
                    block_data = block_data + "<tr><td>miner_tx</td><td><table>"
                    for tx in bd_json[bd].keys():
                        block_data = block_data + "<tr><td>{}</td><td>{}</td></tr>".format(tx, json.dumps(bd_json[bd][tx], indent=True))
                    block_data = block_data + "</table></td></tr>"
                else:
                    block_data = block_data + "<tr><td>{}</td><td>{}</td></tr>".format(bd,json.dumps(bd_json[bd], indent=True))
            block_data = block_data + "</table></td></tr>"
        else:
            block_data = block_data + "<tr><td>{}</td><td><pre>{}</pre></td></tr>".format(k,json.dumps(monero_block[k], indent=True))
    block_data = block_data + "</table>"
    if (exists("block.template.html")):
        with open("block.template.html", 'r') as fh:
            html = fh.read()
        html = html.replace("<!-- SITENAME --!>", config_items['sitename'])
        html = html.replace("<!-- POOL_LOGO --!>", config_items['pool_logo'])
        html = html.replace("<!-- BLOCKDATA --!>", block_data)
    return contype, html

def blockui_page():
    contype = "text/html"
    html = ""
    if (exists("blockui.template.html")):
        with open("blockui.template.html", 'r') as fh:
            html = fh.read()
        html = html.replace("<!-- SITENAME --!>", config_items['sitename'])
        html = html.replace("<!-- POOL_LOGO --!>", config_items['pool_logo'])
    return contype, html

def json_pplns_estimate():
    return time() * 1000 - 2.16e7
    pplns_est = get_pplns_window_estimate(config_items['pooldd'])
    return json_generic_response({"pplns_end":pplns_est})

def json_graph_stats():
    stat_array = []
    highest_p = 0
    highest_n = 0
    highest_p2r = 0
    lowest_p = -1   
    files = get_files(config_items['stats_dir'] + "/*.json")
    unused_var_zero, block_json = json_blocks_all_response()
    blocks = json.loads(block_json)
    now = int(datetime.now().timestamp())
    fifteen_hours_ago = now - 900 * 3600
    blocks_in_last_fifteen = []
    for block in blocks:
        if block['timestamp'] >= fifteen_hours_ago:
            blocks_in_last_fifteen.append(block)
    stat_data = read_files(files)
    sorted_keys = sorted(stat_data)
    # make sure we only have the latest 900 items
    if len(sorted_keys) > 900:
        sorted_keys = sorted_keys[-900:]
    p = 0
    p_sum = 0
    # find the highest value to determine the graph percential
    for my_item in sorted_keys:
        p_sum += stat_data[my_item]['pr']
        p += 1
        if stat_data[my_item]['p2r'] > highest_p2r:
            highest_p2r = stat_data[my_item]['p2r']
        if stat_data[my_item]['nr'] > highest_n:
            highest_n = stat_data[my_item]['nr']
        if stat_data[my_item]['pr'] > highest_p:
            highest_p = stat_data[my_item]['pr']
        if stat_data[my_item]['pr'] < lowest_p or lowest_p == -1:
            lowest_p = stat_data[my_item]['pr']
    if ( p != 0 ):
        p_avg = floor(p_sum / p)
    else:
        p_avg = 0
    if highest_p2r != 0:
        pp = highest_p / highest_p2r
    else:
        pp = 0
    if highest_p != 0: 
        p_avg_d = abs(floor(p_avg / (highest_p) * 150) - 150)
    else:
        p_avg_d = 149
    stat_array = []
    for my_item in sorted_keys:
        percentile = 0
        # the graph draws upside down so we invert the numbers
        percentile = abs(floor(stat_data[my_item]['p2r'] / highest_p2r * 150) - 150)
        stat_data[my_item]['nrp'] = percentile
        percentile = 0
        if highest_p != 0:
            percentile = abs(floor(stat_data[my_item]['pr'] / (highest_p) * 150) - 150)
        else:
            percentile = 149
        stat_data[my_item]['prp'] = percentile
        block_data = None
        for block in blocks_in_last_fifteen:
            if my_item == block['timestamp'] \
                or (my_item - 30 <= block['timestamp']
                and my_item + 30 >= block['timestamp']):
                block_data = block

        stat_array.append(
                { 'nr':  stat_data[my_item]['nr'],
                  'p2r': stat_data[my_item]['p2r'],
                  'pr':  stat_data[my_item]['pr'],
                  'nrp': stat_data[my_item]['nrp'],
                  'prp': stat_data[my_item]['prp'],
                  'nd': stat_data[my_item]['nd'],
                  'pavg': p_avg_d,
                  'ts': my_item,
                  'block': block_data
                  })
    return json_generic_response(stat_array)

def json_get_multi():
    response={}
    response['multi'] = 0
    #pool_stats = moneropool_get_stats(config_items['site_ip'])
    #FIX ME
    unused_var, pool_stats = get_stats()
    pool_stats = json.loads(pool_stats)
    #pool_stats['pool_hashrate'] = 0
    #pool_stats['network_hashrate'] = 0
    pp = pool_stats['pool_hashrate'] / pool_stats['p2pool_hashrate']
    for i in range(0,20):
        multi = 10**i
        if multi * pp > 1:
            break
    response['multi'] = multi
    return json_generic_response(response)

def json_payments_summary():
    response = []
    payments = wallet_get_transfers_out(config_items['wallet_rpc'])
    for payment in payments:
        bb={}
        bb['reward'] = payment['amount']
        if "destinations" in payment:
            bb['miner_count'] = len(payment['destinations'])
        else:
            bb['miner_count'] = 'Unknown'
        bb['timestamp'] = payment['timestamp']
        response.append(bb)
    return json_generic_response(response)

def json_blocks_all_really_response():
    return json_generic_response(get_mined().reverse())

def json_blocks_all_response():
    final_blocks = get_mined()
    final_blocks = final_blocks[:30]
    return json_generic_response(final_blocks)

def json_blocks_response():
    final_blocks = get_mined()
    final_blocks.reverse()
    final_blocks = final_blocks[:30]
    return json_generic_response(final_blocks)

def json_generic_response(generic_item):
    contype = "application/json"
    body = json.dumps(generic_item, indent=True)
    return contype, body

def html_generic_response(generic_item):
    contype = "text/html"
    body = "<html><pre>{}</pre></html>".format(generic_item)
    return contype, body

def get_files(stats_files):
    files = glob(stats_files)
    return files

def read_files(files):
    response = {}
    dt_f = "%Y-%m-%dT%H:%M:%S"
    for filename in files:
        data = ""
        # 01234560123456789012345678
        # latest-2021-03-28T05:11:01+00:00.json
        latest_index = filename.index("latest")
        ts = filename[7+latest_index:26+latest_index]
        dt = datetime.strptime(ts, dt_f)
        ts = int(dt.timestamp())
        with open(filename,'r') as fh:
            data += fh.read()
        temp =  json.loads(data)
        response[ts] = {}
        response[ts]['pr'] = temp['pool_hashrate']
        response[ts]['p2r'] = temp['p2pool_hashrate']
        response[ts]['nr'] = temp['network_hashrate']
        response[ts]['nd'] = temp['network_difficulty']
    return response

def application(environ, start_response):
    request_uri = environ['REQUEST_URI']
    if 'HTTP_COOKIE' in environ.keys():
        cookies = cookiecutter(environ['HTTP_COOKIE'])
        if 'wa' in cookies:
            wa = cookies['wa']
        else:
            wa = None
        if 'dark_mode' in cookies:
            dark_mode = cookies['dark_mode']
        else:
            dark_mode = False
    else:
        dark_mode = False
        wa = None
    parameters = {}
    if "?" in request_uri:
        splitter = request_uri.split("?")
        request_uri = splitter[0]
        parameters = splitter[1]
    if parameters:
        final_p = {}
        para_kv = parameters.split("&")
        for para in para_kv:
            k, v = para.split("=")
            final_p[k]=v
        parameters = final_p
    if len(request_uri) > 128:
        request_uri = request_uri[0:128]
    memcache_client = base.Client(('localhost',11211))
    last_api_time = memcache_client.get("{}_last".format(request_uri))
    usecache = False
    time_multi = 1
    if last_api_time == None:
        last_api_time = 0
    else:
        last_api_time = json.loads(last_api_time)[0]
    now = datetime.now().timestamp()
    if now - last_api_time > (30 * time_multi) or last_api_time == 0 or len(parameters) > 0:
        usecache = False
    else:
        usecache = True
    if "{}pplns_est".format(VERSION_PREFIX) == request_uri:
        usecache = True
    elif "{}payments".format(VERSION_PREFIX) == request_uri:
        usecache = False
    elif "{}blockui.html".format(VERSION_PREFIX) == request_uri:
        usecache = False
    elif "{}payout_est".format(VERSION_PREFIX) == request_uri:
        usecache = False
    elif "{}/workers".format(VERSION_PREFIX) == request_uri:
        usecache = False
    elif "{}/stats".format(VERSION_PREFIX) == request_uri:
        usecache = False
    contype = "text/plain"
    nothing = False
    
    # non parallel friendly! only let one thread do this at a time
    # this will update the memcache result for /0/pplns_est
    # this is the quickest way to make sure only 1 thread
    # executes this at a time.
    # schedule a cronjob to hit curl http://localhost:5252/local/0/pplns_est_generate
    # to update this do not expose this API to the world
    # may the spirits have mercy on you if you do
#    if "/local{}pplns_est_generate".format(VERSION_PREFIX) == request_uri:
#        contype, body = json_pplns_estimate()
#        request_uri = "{}pplns_est".format(VERSION_PREFIX)
#        memcache_client.set("{}_last".format(request_uri), json.dumps([datetime.now().timestamp()]))
#        memcache_client.set("{}_contype".format(request_uri), json.dumps([contype]))
#        memcache_client.set("{}_body".format(request_uri), json.dumps([body]))
    if not usecache:
        if VERSION_PREFIX == request_uri[0:len(VERSION_PREFIX)]:
            if "{}blocks".format(VERSION_PREFIX) == request_uri:
                contype, body = json_blocks_response()
            elif "{}workers".format(VERSION_PREFIX) == request_uri:
                if wa:
                    contype, body = json_generic_response(get_workers_by_wa(config_items['p2pooler_rpc'], config_items['p2pooler_token'], wa))
                else:
                    contype = "application/json"
                    body = ""
            elif "{}stats".format(VERSION_PREFIX) == request_uri:
                contype, body = get_stats(wa)
            elif "{}multi".format(VERSION_PREFIX) == request_uri:
                contype, body = json_get_multi()
            elif "{}blocks.all".format(VERSION_PREFIX) == request_uri:
                contype, body = json_blocks_all_response()
            elif "{}blocks.all.really".format(VERSION_PREFIX) == request_uri:
                contype, body = json_blocks_all_really_response()
            #elif "{}payments".format(VERSION_PREFIX) == request_uri and len(wa) > 0:
            #    contype, body = json_generic_response(get_payments(pooldd, wa))
            elif "{}payments.summary".format(VERSION_PREFIX) == request_uri:
                contype, body = json_payments_summary()
            elif "{}pool.html".format(VERSION_PREFIX) == request_uri:
                contype, body = pool_page()
            elif "{}blockui.html".format(VERSION_PREFIX) == request_uri:
                if parameters:
                    if "block" in parameters.keys():
                        contype, body = block_page(parameters['block'])
                else:
                    contype, body = blockui_page()
            elif "{}data.gif".format(VERSION_PREFIX) == request_uri:
                contype, body = data_gif()
            elif "{}graph_stats.json".format(VERSION_PREFIX) == request_uri:
                contype, body = json_graph_stats()
            #elif "{}bonus_address".format(VERSION_PREFIX) == request_uri:
            #    response = get_latest_winner()
            #    contype, body = json_generic_response(response)
            else:
                contype, body = html_generic_response("I got nothing for you man!")
                nothing = True
        else:
            nothing = True
            body = "This should not be served"
        if not nothing and "{}payments".format(VERSION_PREFIX) != request_uri and "{}blockui.thml".format(VERSION_PREFIX) != request_uri \
            and "{}payout_est".format(VERSION_PREFIX) != request_uri and "{}workers".format(VERSION_PREFIX) != request_uri and "{}/stats".format(VERSION_PREFIX) != request_uri:
            memcache_client.set("{}_last".format(request_uri), json.dumps([datetime.now().timestamp()]))
            memcache_client.set("{}_contype".format(request_uri), json.dumps([contype]))
            memcache_client.set("{}_body".format(request_uri), json.dumps([body]))
    else:
        contype = memcache_client.get("{}_contype".format(request_uri))
        body = memcache_client.get("{}_body".format(request_uri))
        if contype and body:
            contype = json.loads(contype)[0]
            body = json.loads(body)[0]
        else:
            contype = "text/plain"
            body = "cache failure, deleted cache entries"
            memcache_client.delete("{}_last".format(request_uri))
            memcache_client.delete("{}_body".format(request_uri))
            memcache_client.delete("{}_contype".format(request_uri))
    start_response('200 OK', [('Content-Type', contype)])
    return [body.encode('utf-8')]
