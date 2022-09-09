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
REWARDLOG=$BASEPATH/reward.log
CLEANERLOG=$BASEPATH/cleaner.log

cd $BASEPATH
source ../venv/bin/activate
echo -- start -- >> $CLEANERLOG 
echo $(date --iso-8601=s) >> $CLEANERLOG 
python cleaner.py >> $CLEANERLOG 
echo $(date --iso-8601=s) >> $CLEANERLOG 
echo -- end -- >> $CLEANERLOG 

echo -- start -- >> $REWARDLOG
echo $(date --iso-8601=s) >> $REWARDLOG 
count=$(curl -s http://$site/1/needreward | jq '.|length')
if [[ "$count" != "0" ]]; then
    echo "$count blocks found that need to be split" >> $REWARDLOG
    #PAYOUT IS DISABLED BY DEFAULT UNCOMMENT THE NEXT LINE TO ENABLE
    #python reward_splitter.py >> $REWARDLOG  # uncomment to reward splits for payer.py to payout from.
else
    echo "no blocks found that need to be split" >> $REWARDLOG
fi
echo $(date --iso-8601=s) >> $REWARDLOG 
echo -- end -- >> $REWARDLOG
