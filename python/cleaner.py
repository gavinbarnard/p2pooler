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
from time import time


r = redis.Redis()

def fmt_memory(memory):
    size_dict = ['b',
                 'kb',
                 'mb',
                 'gb',
                 'tb'] # fucked if we hit this
    count = 0
    while memory > 10240:
        memory = memory / 1024
        count += 1
        if count == 4:
            break
    return "{} {}".format(round(memory,2), size_dict[count])

def main():
    total_mem_pre_clean = 0
    total_rmem_pre_clean = 0
    total_mem_post_clean = 0
    total_rmem_post_clean = 0
    resp = r.keys("s_*")
    for key in resp:
        s_count = r.json().arrlen(key)
        memory = r.json().debug("MEMORY", key)
        raw_memory = r.memory_usage(key)
        print("before user: {} shares: {} memory: j{} r{}".format(str(key[2:], 'utf-8'), s_count, fmt_memory(memory), fmt_memory(raw_memory)))
        total_mem_pre_clean += memory
        total_rmem_pre_clean += raw_memory
        ts_list = r.json().get(key, "$..timestamp")
        ts = int(time() * 1000) 
        last_found = -1
        for i in range(len(ts_list)):
            if ts - ts_list[i] > 64836000:
                last_found = i
            else:
                break
        if last_found == -1:
            print("no shares to kill")
        else:
            print("keeping shares {} to {}".format(last_found + 1, s_count - 1))
            r.json().arrtrim(key, "$", last_found + 1, s_count - 1)
        s_count = r.json().arrlen(key)
        if s_count == 0:
            r.json().forget(key)
            print("dropping {} key because no shares remain".format(str(key, 'utf-8')))
        else:
            last_ts = r.json().get(key, "$[{}].timestamp".format(s_count - 1))
            memory = r.json().debug("MEMORY", key)
            raw_memory = r.memory_usage(key)
            total_mem_post_clean += memory
            total_rmem_post_clean += raw_memory
            print("after user: {} shares: {} last share at: {} memory: j{} r{}".format(str(key[2:], 'utf-8'), s_count, last_ts, fmt_memory(memory), fmt_memory(raw_memory)))
    print("total memory before/after clean: j{} / {} - r{} / {}".format(fmt_memory(total_mem_pre_clean), fmt_memory(total_mem_post_clean), fmt_memory(total_rmem_pre_clean), fmt_memory(total_rmem_post_clean)))
    mstats = r.memory_stats()
    print("peak alloc: {}".format(fmt_memory(mstats['peak.allocated'])))
    print("total allocated: {}".format(fmt_memory(mstats['total.allocated'])))
    print("key count: {}".format(mstats['keys.count']))
    print("bytes per key: {}".format(fmt_memory(mstats['keys.bytes-per-key'])))
    print("dataset size: {}".format(fmt_memory(mstats['dataset.bytes'])))

if __name__ == "__main__":
    main()