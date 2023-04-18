import logging
from select import select
import socket
import socketserver
import threading
from jsonrpcclient import Ok, parse_json, request_json as _request_json
from json import dumps, loads
from json.decoder import JSONDecodeError
from time import time

pools = {
    "mini": ("127.0.0.1", 3333),
    "main": ("127.0.0.1", 3334)
}


def request_json(method, params):
    req = _request_json(method, params)
    req += "\n"
    return req


class Backendhandler:
    def __init__(self, backend="mini"):
        self.sock = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.backend = backend
        self.buffer = None
        self.job_id = None
        self.target = None
        self.seed_hash = None
        self.height = None
        self.blob = None
        self.last_job_json = None
        self.connect()
        self.login()

    def connect(self):
        self.sock.connect(pools[self.backend])
    
    def login(self):
        req = request_json("login", {"login": "gavin", "algo": ['rx/0'], 'agent': "proxywithamoxy", 'rigid': 'proxywithamoxy'})
        self.sock.sendall(bytes(req, 'utf-8'))
        result = self.sock.recv(1024)
        resp = parse_json(str(result, 'utf-8'))
        if isinstance(resp, Ok):
            self.buffer = str(result, 'utf-8')
    
    def process_buffer(self):
        if self.buffer:
            s = self.buffer.split("\n")
            for m in s:
                if len(m) > 0:
                    msg = loads(m)
                    params = None
                    if "result" in msg.keys():
                        params = msg['result']['job']
                    elif "method" in msg.keys():
                        params = msg['params']
                    p_list = ['job_id', 'target', 'seed_hash', 'blob', 'height']
                    for p in p_list:
                        if p not in params.keys():
                            self.buffer = None
                            logging.warning(f"missing field {p}")
                            return
                    self.job_id = params['job_id']
                    self.target = params['target']
                    self.seed_hash = params['seed_hash']
                    self.blob = params['blob']
                    self.height = params['height']
                    self.last_job_json = request_json("job", params)
            self.buffer = None

    def check_sock(self):
        while self.buffer:
            self.process_buffer()
        r, w, e = select([self.sock], [], [])
        for s in r:
            data = self.sock.recv(1024)
            self.buffer = str(data, 'utf-8')
        while self.buffer:
            self.process_buffer()



class Frontendhandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = str(self.request.recv(1024), 'utf-8')
        cur_thread = threading.current_thread()
        #response = bytes("{}: {}".format(cur_thread.name, data), 'utf-8')
        resp = None
        try:
            resp = loads(data)
        except JSONDecodeError as e:
            logging.warning("{} - {} not a jsonrpc response - {}".format(cur_thread, data, e))
        if resp:
            self.process_jsonrpc(resp)

    def push_update(self):
        self.request.sendall(self.backend.last_job_json)

    def print_garbage(self, garbage):
        print(garbage)

    def process_jsonrpc(self, msg):
        print(self.backend.last_job_json)
        print(msg['method'])
        #{"id":1,"jsonrpc":"2.0",
        # "result":
        #   {
        #   "id":"30a4b07d",
        #   "job":
        #    {
        #       "blob":"1010a2a4b9a106991b4c8809ecccef4622ee50b53a303758d639c04180edd2d61c3047b2d2d84f0000000044f32adb9047577fa7ed7862d3c97ee6c0f36924e37703aea6ff2f84fe3eaa0b03",
        #       "job_id":"1","target":"31040000","algo":"rx/0","height":2858106,"seed_hash":"3c8c69f3ca15d9e9a5c2ec6dc1608ba8ae6a81df2fea4799248a9c16fb355cd0"
        #    },
        #    "extensions":["algo"],"status":"OK"}
        # }
        
        if msg['method'] == 'login':
            resp = {
               "id": 1,
               "jsonrpc": "2.0",
               "result": {
                "id": "30ffb77d",
                "job": loads(self.backend.last_job_json)['params']
               },
               "extensions": ["algo"],
               "status": "OK"
            }
            self.request.sendall(bytes(dumps(resp), 'utf-8'))
        else:
            self.request.sendall(self.backend.last_job_json)

class ThreadedFrontendhandler(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def main():
    logging.basicConfig(level = logging.DEBUG)
    server = ThreadedFrontendhandler(("0.0.0.0", 6666), Frontendhandler)
    with server:
        server_thread = threading.Thread(target=server.serve_forever, name="frontend")
        server_thread.daemon = True
        server_thread.start()
        while True:
            pass

if __name__ == "__main__":
    main()