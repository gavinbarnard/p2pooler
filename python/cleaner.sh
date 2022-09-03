#!/bin/bash

cd /home/monero/p2pooler/python
source ../venv/bin/activate
echo -- start -- >> /home/monero/p2pooler/python/cleaner.log
echo $(date --iso-8601=s) >> /home/monero/p2pooler/python/cleaner.log
python cleaner.py >> /home/monero/p2pooler/python/cleaner.log
echo $(date --iso-8601=s) >> /home/monero/p2pooler/python/cleaner.log
echo -- end -- >> /home/monero/p2pooler/python/cleaner.log
