#!/bin/bash
cd crawler
echo "--- crawler.sh"
export PATH=$PATH:~/.local/bin
scrapy crawl test_spider -a url=$1