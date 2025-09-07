import sys
import socket
import json
from util.config import parse_config, cli_options

config_items = parse_config(cli_options())

p2pool_stats_dir = config_items['p2pool_stats']

with open(f'{p2pool_stats_dir}/local/console', 'r') as file:
    data = json.load(file)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('127.0.0.1', data['tcp_port']))

command = data['cookie']
command += "status"
command += '\n'

s.sendall(command.encode('utf-8'))
s.close()
