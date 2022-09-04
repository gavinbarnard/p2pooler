#!/usr/bin/env python

import redis
import json

r = redis.Redis()

def main():
    dump_me = []
    resp = r.keys("s_*")
    for key in resp:
        dk = r.json().get(key)
        dump_me.append(dk)
    with open("dump.json", 'w') as fh:
        fh.write(json.dumps(dk, indent=True))

if __name__ == "__main__":
    main()