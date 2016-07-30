# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
from InstaCrawler import  settings
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from InstaCrawler.items import InstacrawlerItem

from seleniumscraper import InstagramCrawler
from selenium import webdriver

import json
import re
import  selenium
from selenium.common.exceptions import NoSuchElementException, WebDriverException



def load(filename):
    datastr = open(filename).read()
    data = json.loads(datastr)
    return data


class InstaSpider(scrapy.Spider):
    name = "insta"
    allowed_domains = ["instagram.com"]
    start_urls = [
        'https://www.instagram.com/explore/tags/shopping',
    ]

    def __init__(self):
        print ("************")
        # user_input = raw_input("Enter: tag")
        # hash = user_input
        super(InstaSpider, self).__init__()
        self.data = load("InstaCrawler/data/login_data/login_details.json")
        self.driver = webdriver.Chrome()
        self.post_driver = webdriver.Chrome()
        self.instagram = InstagramCrawler(self.driver, self.data)
        self.instagram.run()


    def parse(self, response):

        self.driver.get(response.url)
        load_more_btn = self.driver.find_element_by_class_name('_oidfu')
        load_more_btn.click()


        most_recent_div_selectors = self.driver.find_elements_by_xpath("//div[@class='_nljxa']")[1]

        """ Will replace for loop with infine while loop"""
        """ Scroll window for 99 times """
        for x in range(1,10):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);",most_recent_div_selectors)
            time.sleep(1)

        """ Get all post hrefs after scrolling  finished """

        # post_hrefs = most_recent_post_div_selector.find_elements_by_xpath(".//a")
        for link in most_recent_div_selectors.find_elements_by_xpath(".//a"):
            print("********")
            print(link.get_attribute('href'))
            yield scrapy.Request(link.get_attribute('href'), callback=self.parse_post, dont_filter=True)



    def parse_post(self,response):
        print ("****************")
        print (response.url)

        print("*************")
        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        post_data_text = json_shared_data.group(2)
        post_data_dict = json.loads(post_data_text, strict=False)

        post_data = post_data_dict['entry_data']['PostPage'][0]['media']

        username = post_data['owner']['username']
        link_to_user = 'https://www.instagram.com/{}'.format(username)
        likes_count = post_data['likes']['count']
        comments_count = post_data['comments']['count']
        post_date_in_epoch = float(post_data['date'])
        post_date = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime(post_date_in_epoch))
        captions = post_data['caption']

        """ Extraction of user and comments """
        self.post_driver.get(response.url)
        self.post_driver.find_element_by_xpath("//ul[@class='_mo9iw _123ym']")
        """ First click view all button """
        try:
            view_all_comments_btn = self.post_driver.find_element_by_xpath('//button[@class="_l086v _ifrvy"]')
            if view_all_comments_btn:
                view_all_comments_btn.click()
        except (selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.WebDriverException):
            print("No View all Button")

        """ Click load more button until it is available"""
        i = 0
        load_more_btn = True
        while load_more_btn:
            try:
                btn1 = self.post_driver.find_element_by_xpath('//li/button[@class=disabled=""]')
                if btn1:
                    btn1.click()
                    print(i)
                time.sleep(1)
            except (selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.WebDriverException):

                print('End of  Load More button')
                load_more_btn = False
            i += 1
        """ Extract comments after finished loading all comments elements"""
        users_elem = self.post_driver.find_elements_by_xpath("//li[@class='_nk46a']/a")
        comments_elem = self.post_driver.find_elements_by_xpath("//li[@class='_nk46a']/span")
        i = 1
        comments_dict_list = []
        for user, comment in zip(users_elem, comments_elem):
            comment_dict = {}
            print(i, user.get_attribute('title'))
            username = user.get_attribute('title')
            user_link = user.get_attribute('href')
            comment = comment.text
            comment_dict['user'] = {
                'username':username,
                'user link':user_link
            }
            comment_dict['comment'] = comment
            comments_dict_list.append(comment_dict)
            i += 1


        request = scrapy.Request(link_to_user,callback=self.parse_user,dont_filter=True)
        request.meta['username'] = username
        request.meta['likes_count'] = likes_count
        request.meta['comments_count'] = comments_count
        request.meta['post_date'] = post_date
        request.meta['link_to_the_post'] = response.url
        request.meta['influence_handle'] = link_to_user
        request.meta['captions'] = captions
        request.meta['comments'] = comments_dict_list

        yield request

    def parse_user(self, response):

        print "**********"
        print (response.url)
        print "**********"

        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        user_data_text = json_shared_data.group(2)
        user_data_dict = json.loads(user_data_text, strict=False)

        user_data = user_data_dict['entry_data']['ProfilePage'][0]['user']

        followers_count = user_data['followed_by']['count']

        """" ************** Caption **************** """

        captions = response.meta['captions']

        """ Extracting Website from captions """
        website_regex = re.compile(
            r'((https?:\/\/)?'
            r'(www\.)?'
            r'[-a-zA-Z0-9@:%._\+~#=]{2,256}'
            r'\.'
            r'[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*))')

        website_group = re.findall(website_regex, captions)
        websites =[]
        for link in website_group:
            print(link[0])
            websites.append(link[0])

        """ Extraction hash tags from captions"""
        other_hash_tags = re.findall(r'(#[a-zA-Z0-9:%._\+~#=]+)', captions)

        """ EXtraction of influence Followers from captions"""
        influence_followers = re.findall(r'(@[a-zA-Z0-9:%._\+~#=]+)', captions)

        """ Post Item  """
        item = InstacrawlerItem()

        item['Post'] = {
            "Unique Identifier": response.meta['username'],
            "Link To The Post": response.meta['link_to_the_post'],
            "Influence Handle": response.meta['influence_handle'],
            "Influence Follower": influence_followers,
            "Post Likes":{
                "count": response.meta['likes_count']
                },
            "Post Comments": {
                "count": response.meta['comments_count'],
                "comments":response.meta['comments']
                },
            "Engagement": int(response.meta['comments_count'])+int(response.meta['likes_count']),
            "Other Hash Tags":other_hash_tags,
            "Other Account Tags": websites,
            "Link To Bio": response.url,

            "Date of Post":  response.meta['post_date'],
            "Followers":{
                "count": followers_count
            }


        }

        yield item

















