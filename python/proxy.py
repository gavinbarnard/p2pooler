import socket
from select import select
import time
import sys
from json import dumps, loads
import binascii
import struct
import logging
import redis
from util.validator import validate_address
from util.config import cli_options, parse_config

config_options =  parse_config(cli_options())
r = redis.Redis(port=config_options['redis_port'])

# Changing the buffer_size and delay, you can improve the speed and bandwidth.
# But when buffer get to high or delay go too down, you can broke things
buffer_size = 4096
delay = 0.0001
forward_to_mini = ('localhost', 3333)
forward_to_main = ('localhost', 3334)


class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, connect_tuple):
        try:
            self.forward.connect(connect_tuple)
            return self.forward
        except Exception as e:
            logging.error(e)
            return False

class Proxy:
    input_list = []
    channel = {}
    usermap = {}
    now = 0
    last = 0
    lifetime_accepted = 0
    lifetime_rejected = 0
    report_delay = 30
    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

    def main_loop(self):
        self.input_list.append(self.server)
        while 1:
            now = time.time()
            if (now - self.last) > self.report_delay:
                logging.info("accepted: {} rejected: {} - Connected users: {}".format(self.lifetime_accepted, self.lifetime_rejected, len(self.usermap)))
                self.last = time.time()
            #time.sleep(delay)
            inputready, outputready, exceptready = select(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                self.data = self.s.recv(buffer_size)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        forward = Forward().start(forward_to_mini)
        clientsock, clientaddr = self.server.accept()
        if forward:
            logging.debug("{} has connected".format(clientaddr))
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
            userkey = "{}:{}".format(clientaddr[0], clientaddr[1])
            self.usermap[userkey] = { "forward": forward, "clientsock": clientsock, "login": "", "job":{}, "submitted": [], "accepted": 0, "rejected": 0}
        else:
            logging.error("Can't establish connection with remote server.")
            logging.error("Closing connection with client side {}".format(clientaddr))
            clientsock.close()

    def on_close(self):
        logging.debug("{} has disconnected".format(self.s.getpeername()))
        #remove from usermap
        peerdata = self.s.getpeername()
        peerkey = "{}:{}".format(peerdata[0],peerdata[1])
        if peerkey in self.usermap.keys():
            del self.usermap[peerkey]
        #remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        # here we can parse and/or modify the data before send forward
        msg = None
        if data[0:4] == b'\x16\x03\x01\x01':
            logging.warning("{} SSL connect attempt".format(self.s.getpeername()))
            self.on_close()
            return
        try:
            msg = loads(str(data, 'utf-8'))
        except Exception as e:
            logging.error("caught exception while processing payload {}, data {}".format(e, data[0:10]))
        target = None
        userkey = None
        direction = None
        user = None
        for i in self.usermap.keys():
            if self.usermap[i]['forward'] == self.s:
                direction = "forward"
                userkey = i
            elif self.usermap[i]['clientsock'] == self.s:
                direction = "client"
                userkey = i
        if userkey and direction and msg:
            user = self.usermap[userkey]['login']
            if "method" in msg.keys():
                if msg['method'] == "login":
                    self.usermap[userkey]['login'] = msg['params']['login']
                    user = msg['params']['login']
                elif msg['method'] == "job":
                    target = msg['params']['target']
                    self.usermap[userkey]['job'] = msg
                elif msg['method'] == "submit":
                    self.usermap[userkey]['submitted'].append(msg)
                else:
                    logging.warning("unhandled method {}".format(msg))
                logging.debug("{} {} {} {}".format(userkey, msg['method'], user, msg))
            elif "result" in msg.keys():
                if "job" in msg['result'].keys():
                    target = msg['result']['job']['target']
                    #self.usermap[userkey]['job'] = msg
                elif "status" in msg['result'].keys():
                    r_list = []
                    for submitted in self.usermap[userkey]['submitted']:
                        if submitted['params']['job_id'] == self.usermap[userkey]['job']['params']['job_id']:
                            diff = self.usermap[userkey]['job']['params']['target']
                            target = diff
                            if diff:
                                diff = struct.unpack('I', binascii.unhexlify(diff))[0]
                                if diff >> 32 == 0:
                                    diff = int(0xFFFFFFFFFFFFFFFF / 0xFFFFFFFF / diff)
                            if msg['result']['status'] == "OK":
                                self.usermap[userkey]['accepted'] += 1
                                self.lifetime_accepted += 1
                                logging.debug("accepted share diff {} {} {} total a:{} r:{}".format(userkey, diff, self.usermap[userkey]['login'], self.usermap[userkey]['accepted'], self.usermap[userkey]['rejected']))
                                if validate_address(user):
                                    share_key = "s_{}".format(user)
                                    my_dict = {
                                        "timestamp": int(time.time() * 1000),
                                        "diff": diff
                                    }
                                    try:
                                        resp = r.json().arrappend(share_key, "$", my_dict)
                                    except redis.exceptions.ResponseError as e:
                                        if str(e) == "could not perform this operation on a key that doesn't exist":
                                            resp = r.json().set(share_key, "$", [])
                                            if resp:
                                                resp = r.json().arrappend(share_key, "$", my_dict)
                                    if not resp:
                                        logging.error("unable to record share for user {} ts {} diff {}", share_key, my_dict['ts'], my_dict['diff'])
                                else:
                                    logging.warning("user {} is not a valid monero address".format(user))
                            else:
                                self.usermap[userkey]['rejected'] += 1
                                self.lifetime_rejected += 1
                                logging.warning("rejected share diff {} {} {} total a:{} r:{}".format(userkey, diff, user, self.usermap[userkey]['accepted'], self.usermap[userkey]['rejected']))
                            r_list.append(submitted)
                    for remove_me in r_list:
                        self.usermap[userkey]['submitted'].remove(remove_me)
                else:
                    logging.warning("unhandled result {}".format(msg['result']))
            if target:
                target = struct.unpack('I', binascii.unhexlify(target))[0]
                if target >> 32 == 0:
                    target = int(0xFFFFFFFFFFFFFFFF / 0xFFFFFFFF / target)
            logging.debug("{} {} {} {}".format(userkey, target, direction, user))
        self.channel[self.s].send(data)


if __name__ == '__main__':
        log_format = "%(asctime)s - %(levelname)s - %(message)s" 
        logging.basicConfig(format = log_format, level = logging.DEBUG)
        server = Proxy('', 4246)
        logging.warning("Starting Proxy")
        try:
            server.main_loop()
        except KeyboardInterrupt:
            logging.warning("Ctrl C - Stopping Proxy")
            sys.exit(1)