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

import os
import json
import argparse
import sys


def cli_options():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", action="store", default=os.environ['HOME'] + "/.config/p2pooler-py.json")
    args = ap.parse_args()
    if args.config:
        return args.config
    else:
        ap.print_help()
        exit(1)

def parse_config(config_file):
    if os.path.isfile(config_file):
        config = json.loads(open(config_file,'r').read())
        config_keys = [
            "monero_rpc",
            "monero_ip",
            "wallet_rpc",
            "receiver_port",
            "redis_port",
            "v1_template_html",
            "p2pool_stats",
            "p2pooler_rpc",
            "p2pooler_token"
        ]
        for key in config_keys:
            if key not in config.keys():
                sys.stderr.write("missing config key {}".format(key))
                raise(KeyError("missing configuration key {}".format(key)))
                exit(1)
    else:
        sys.stderr.write("error reading config file {}".format(config_file))
        exit(1)
    return config
