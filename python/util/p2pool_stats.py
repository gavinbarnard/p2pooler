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
from os.path import exists

STAT_FILES = ['network', 'local', 'pool']

def get_stat(stat_dir, stat_type):
    resp = None
    if stat_type == "stats_mod":
        filename = "{}/stats_mod".format(stat_dir)
    else:
        if stat_type in STAT_FILES:
            filename = "{}/{}/stratum".format(stat_dir, stat_type)
    if exists(filename):
        with open(filename, 'r') as fh:
            resp = fh.read()
    if resp:
        resp = json.loads(resp)
    return resp