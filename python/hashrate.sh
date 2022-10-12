#!/bin/bash


CONFIG_FILE=~/.config/p2pooler-py.json

jq . $CONFIG_FILE

if [ $? != 0 ];
then
	echo bad config
	exit;
fi

site=`jq -r .site_ip $CONFIG_FILE`

BASEPATH=/home/monero/p2pooler/python

cd $BASEPATH
source ../venv/bin/activate
python hashrate.py  
