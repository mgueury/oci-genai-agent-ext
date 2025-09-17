#!/bin/bash
cd crawler
echo "--- crawler.sh"
export PATH=$PATH:~/.local/bin
source ../../myenv/bin/activate
scrapy crawl $1 -a url=$2