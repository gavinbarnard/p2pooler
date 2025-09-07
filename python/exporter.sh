#!/bin/bash

CONFIG_FILE=~/.config/p2pooler-py.json

jq . $CONFIG_FILE

if [ $? != 0 ];
then
	echo bad config
	exit;
fi

STATS_DIR=`jq -r .stats_dir $CONFIG_FILE`
site=`jq -r .site_ip $CONFIG_FILE`
logfile=`jq -r .p2pool_log $CONFIG_FILE`
find $STATS_DIR -name \*.json -mmin +910 -delete
curl -s http://$site/1/stats > $STATS_DIR/latest-`date --iso-8601=seconds`.json
find $STATS_DIR -name \*.json -size -300c -delete # removes broken stats files

BASEPATH=/home/monero/p2pooler/python

cd $BASEPATH
source ../venv/bin/activate
python3 p2pool_console_status.py
sleep .25
grep "Your shares               = " $logfile | awk '{print "{\"shares\": " $4 ",\"uncles\": " substr($6,3) ",\"orphans\": " $8"}"'} | tail -1 > $STATS_DIR/shares.json
grep "Your shares po" $logfile | awk '{print $5}' | tail -1 > $STATS_DIR/shares_window
