# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import codecs
json_path = "data/extracted_data/"

class InstacrawlerPipeline(object):

    def __init__(self):
        self.file = codecs.open('{}instagram_crawled_data1.json'.format(json_path),'wb',encoding='utf-8')

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item





