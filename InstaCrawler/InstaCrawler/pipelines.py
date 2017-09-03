# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import json
import codecs
json_path = "data/extracted_data/"
from InstaCrawler.spiders.insta import InstaSpider


class InstacrawlerPipeline(object):

    # def __init__(self):
    #     self.file = codecs.open('{}{}.json'.format(json_path, item['Post']['Tag']), 'wb', encoding='utf-8')

    def process_item(self, item, spider):
        self.file = codecs.open('{}{}.json'.format(json_path, item['Tag']['tag_name']), 'a', encoding='utf-8')
        line = json.dumps(dict(item['Tag']['Post'])) + "\n"
        self.file.write(line)

        return item





