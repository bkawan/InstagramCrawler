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
import time
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
        super(InstaSpider, self).__init__()

        self.infinite_loop = True
        self.tag = self.get_hastag_input()

        while not self.tag:
            self.tag = self.get_hastag_input()

        self.start_urls = ['https://www.instagram.com/explore/tags/%s' % self.tag.strip()]

        print("Please Enter Start Date below: ")
        self.start_date = self.get_date_input()

        while not self.start_date:
            print("Please Enter Start Date below: ")

            self.start_date = self.get_date_input()

        print("Please Enter End Date below: ")
        self.end_date = self.get_date_input()

        while not self.end_date:
            print("Please Enter End Date below: ")
            self.end_date = self.get_date_input()

        """ Converting date format to epoch"""
        self.start_epoch = (time.mktime(time.strptime(self.start_date, '%d/%m/%Y'))) - time.timezone
        self.end_epoch = (time.mktime(time.strptime(self.start_date, '%d/%m/%Y'))) - time.timezone


        """ For Testing uncomment this and assign epoch time  """
        # self.start_epoch = 1470125759
        # self.end_epoch = 1470125797

        """ GET MINIMUM FOLLOWERS """
        self.min_followers = self.get_min_followers_input()
        while not self.min_followers:
            self.min_followers = self.get_min_followers_input()

        """ LOAD login_details.json data for login process"""
        self.data = load("data/login_data/login_details.json")
        self.driver = webdriver.Chrome()
        self.post_driver = webdriver.Chrome()
        self.instagram = InstagramCrawler(self.driver, self.data)
        self.instagram.run()

    def spider_closed(self, spider):
        self.driver.close()
        self.post_driver.close()

    def parse(self, response):
        self.driver.get(response.url)
        div_selectors = self.driver.find_elements_by_xpath("//div[@class='_nljxa']")[1]
        load_more_btn = self.driver.find_element_by_class_name('_oidfu')
        load_more_btn.click()
        slicing = 0
        x = 0

        while self.infinite_loop:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            anchor_element = div_selectors.find_elements_by_xpath('.//a[@class="_8mlbc _vbtk2 _t5r8b"]')
            temp_i = len(anchor_element)
            anchor_element = anchor_element[slicing:]
            for anchor in anchor_element:
                yield scrapy.Request(anchor.get_attribute('href'), callback=self.parse_post, dont_filter=True)
            slicing = temp_i
            x += 1
            time.sleep(10)


    def parse_post(self, response):
        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        post_data_text = json_shared_data.group(2)
        post_data_dict = json.loads(post_data_text, strict=False)
        post_data = post_data_dict['entry_data']['PostPage'][0]['media']

        post_date_in_epoch = float(post_data['date'])

        if self.end_epoch >= post_date_in_epoch:

            request = scrapy.Request(response.url, callback=self.parse_check_end_date, dont_filter=True)
            yield request
        else:
            pass
            # self.driver.close()

    def parse_check_end_date(self,response):

        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        post_data_text = json_shared_data.group(2)
        post_data_dict = json.loads(post_data_text, strict=False)
        post_data = post_data_dict['entry_data']['PostPage'][0]['media']

        username = post_data['owner']['username']
        likes_count = post_data['likes']['count']
        comments_count = post_data['comments']['count']
        link_to_user = 'https://www.instagram.com/{}'.format(username)
        captions = post_data['caption']

        post_date_in_epoch = float(post_data['date'])
        post_date = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(post_date_in_epoch))

        if post_date_in_epoch >= self.start_epoch:

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
                except (
                            selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.WebDriverException):

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
                    'username': username,
                    'user link': user_link
                }
                comment_dict['comment'] = comment
                comments_dict_list.append(comment_dict)
                i += 1

            request = scrapy.Request(link_to_user, callback=self.parse_user, dont_filter=True)

            request.meta['username'] = username
            request.meta['likes_count'] = likes_count
            request.meta['comments_count'] = comments_count
            request.meta['post_date'] = post_date
            request.meta['link_to_the_post'] = response.url
            request.meta['captions'] = captions
            request.meta['comments'] = comments_dict_list
            request.meta['comments'] = comments_count

            yield request
        else:
            self.infinite_loop = False
            # self.post_driver.close()
            # self.driver.close()

    def parse_user(self, response):
        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        user_data_text = json_shared_data.group(2)
        user_data_dict = json.loads(user_data_text, strict=False)

        user_data = user_data_dict['entry_data']['ProfilePage'][0]['user']
        link_in_bio =user_data['external_url']

        followers_count = user_data['followed_by']['count']


        """" ************** Caption **************** """

        captions = response.meta['captions']

        """ Extraction hash tags from captions"""
        other_hash_tags = re.findall(r'(#[a-zA-Z0-9:%._\+~#=]+)', captions)
        other_hash_tags = [hash_tags.replace("#", '') for hash_tags in other_hash_tags]

        """ Remove input tag from other hash tag"""
        try:
            other_hash_tags.remove(self.tag)
        except (ValueError or IndexError):
            pass


        """ EXtraction of other account tags"""
        other_account_tags = re.findall(r'(@[a-zA-Z0-9:%._\+~#=]+)', captions)

        """ Post Item  """

        if int(followers_count) >= int(self.min_followers):
            item = InstacrawlerItem()

            item['Post'] = {
                "Unique Identifier": response.meta['username'],
                "Link To The Post": response.meta['link_to_the_post'],
                "Influence Handle": "@{}".format(response.meta['username']),
                "Post Likes":{
                    "count": response.meta['likes_count']
                    },
                "Post Comments": {
                    "count": response.meta['comments_count'],
                    "comments":response.meta['comments']
                    },
                "Engagement": int(response.meta['comments_count'])+int(response.meta['likes_count']),
                "Other Hash Tags":other_hash_tags,
                "Other Account Tags": other_account_tags,
                "Link in Bio": link_in_bio,

                "Date of Post":  response.meta['post_date'],
                "Followers":{
                    "count": followers_count
                }
            }
            yield item

    def get_hastag_input(self):
        hashtag = raw_input("Enter Hash Tag#(shopping): ")
        group = re.search(r'^\w+(.*)', hashtag)
        if group:
            return group.group()
        else:

            print("ERROR!!!! HASH tag Format Error!! Starts with either Alpha or Numeric'")
            return False

    def get_date_input(self):

            date = raw_input("Enter Date (dd/mm/yyyy): ")
            group = re.search(r'(\d{2})[/.-](\d{2})[/.-]20(\d{2})$',date)

            if group:
                return group.group()
            else:

                print("ERROR!!!! Date Format Error!! please Check the format'")
                return False

    def get_min_followers_input(self):

            followers = raw_input("Enter Minimum Followers(+ve numbers only): ")
            group = re.search(r'^[0-9]+$', followers)

            if group:
                return group.group()
            else:

                print("ERROR!!!! Only +ve Integer!! please Check the format'")
                return False



















