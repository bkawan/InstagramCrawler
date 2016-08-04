# -*- coding: utf-8 -*-
import scrapy
from scrapy.shell import inspect_response
from InstaCrawler.items import InstacrawlerItem
from seleniumscraper import InstagramCrawler
from selenium import webdriver
import time
import json
import re
import selenium
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
        self.tag = self.input_hash_tag_checker()
        self.start_urls = ['https://www.instagram.com/explore/tags/%s' % self.tag.strip()]
        date_checker = self.input_date_checker()
        self.start_epoch = date_checker[0]
        self.end_epoch = date_checker[1]
        self.min_followers = self.input_min_followers_checker()

        print("************************************************************")
        print("Start Epich :", self.start_epoch,"End Epoch:", self.end_epoch)
        print("Start Date(Local Date) :",time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(self.start_epoch)),
                                                       "End Date(Local Date:",time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(self.end_epoch)))
        print("Tag to Crawl: ",self.tag)
        print("Minimum Followers: ",self.min_followers)
        print("**********************************************************")

        # print("****************")
        # print(self.tag,self.start_epoch,self.end_epoch,self.min_followers)
        # print("**************")
        # time.sleep(20)

        """ For Testing uncomment this and assign epoch time  """
        # self.start_epoch = 1470162607
        # self.end_epoch =   1470162659


        """ LOAD login_details.json data for login process"""
        try:
            self.data = load("data/login_data/login_details.json")
        except:
            print("*****************************")
            print("Crawling without Login ")
            print("*****************************")
            pass
        self.driver = webdriver.Chrome()
        self.post_driver = webdriver.Chrome()
        try:
            self.instagram = InstagramCrawler(self.driver, self.data)
            self.instagram.run()
        except:
            print("*****************************")
            print("Crawling without Login ")
            print("*****************************")
            pass

    def spider_closed(self, spider):
        self.driver.close()
        self.post_driver.close()

    def parse(self, response):
        self.driver.get(response.url)
        try:
            """ Select Most Recent Post Div Elements"""
            div_selectors = self.driver.find_elements_by_xpath("//div[@class='_nljxa']")[1]
        except IndexError:
            print("*******************************************************************************")
            div_selectors = ""
            self.logger.error("Most Recent Post Div Elements not found")
            print("********************************************************************************")

            pass

        try:
            load_more_btn = self.driver.find_element_by_class_name('_oidfu')
        except selenium.common.exceptions.NoSuchElementException:
            self.logger.error("ERROR!! Either no posts related to hashtag [{}]found  or no Load more button Found ".format(self.tag))
            load_more_btn = False
        if load_more_btn:
            load_more_btn.click()
        slicing = 0
        x = 0

        while self.infinite_loop:

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")


            try:
                anchor_element = div_selectors.find_elements_by_xpath('.//a[@class="_8mlbc _vbtk2 _t5r8b"]')
            except:
                print("***************************************************************")
                self.logger.error(
                    "ERROR!! There is not div selector element for the post tag [{}] ".format(
                        self.tag))
                print("***************************************************************")

                anchor_element = []

            if slicing == len(anchor_element):
                self.infinite_loop = False
            temp_i = len(anchor_element)
            anchor_element = anchor_element[slicing:]
            for anchor in anchor_element:
                yield scrapy.Request(anchor.get_attribute('href'), callback=self.parse_check_end_Date, dont_filter=True)
            slicing = temp_i
            x += 1
            time.sleep(10)

    def parse_check_end_Date(self, response):
        json_shared_data = re.search('(window._sharedData\s=\s)(.*)(;<\/script>)', response.body)
        post_data_text = json_shared_data.group(2)
        post_data_dict = json.loads(post_data_text, strict=False)
        post_data = post_data_dict['entry_data']['PostPage'][0]['media']
        post_date_in_epoch = float(post_data['date'])

        if self.end_epoch >= post_date_in_epoch:
            request = scrapy.Request(response.url, callback=self.parse_check_start_date, dont_filter=True)
            yield request
        else:
            print("******************************************************************************************")
            self.logger.error("Error!! There are no post between the date range {} - {} "
                              .format(time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(self.start_epoch)),
                                      time.strftime("%d-%m-%Y %H:%M:%S", time.localtime(self.end_epoch))))
            print("******************************************************************************************")

            pass

    def parse_check_start_date(self, response):

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
                self.logger.error("The is no View all button in comments")

            """ Click load more button until it is available"""
            i = 0
            load_more_btn = True
            while load_more_btn:
                try:
                    btn1 = self.post_driver.find_element_by_xpath('//li/button[@class=disabled=""]')
                    if btn1:
                        btn1.click()
                        print(i)
                    time.sleep(5)
                except (
                            selenium.common.exceptions.NoSuchElementException or selenium.common.exceptions.WebDriverException):
                    print("*****************************************************")
                    self.logger.error("End of  Load More button")
                    print("*****************************************************")

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
        link_in_bio = user_data['external_url']

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
            print("***********************************************************************************************")
            self.logger.error("Error In Removing Hash Tag or There is no Hast Tag [{}] in captions".format(self.tag))
            print("************************************************************************************************")

            pass

        """ EXtraction of oter account tags"""
        other_account_tags = re.findall(r'(@[a-zA-Z0-9:%._\+~#=]+)', captions)

        """ save Tag item """
        if int(followers_count) >= int(self.min_followers):
            item = InstacrawlerItem()

            item['Tag'] = {
                "tag_name": self.tag,
                "Post": {
                    "Unique Identifier": response.meta['username'],
                    "Link To The Post": response.meta['link_to_the_post'],
                    "Influence Handle": "@{}".format(response.meta['username']),
                    "Post Likes": {
                        "count": response.meta['likes_count']
                    },
                    "Post Comments": {
                        "count": response.meta['comments_count'],
                        "comments": response.meta['comments']
                    },
                    "Engagement": int(response.meta['comments_count']) + int(response.meta['likes_count']),
                    "Other Hash Tags": other_hash_tags,
                    "Other Account Tags": other_account_tags,
                    "Link in Bio": link_in_bio,

                    "Date of Post": response.meta['post_date'],
                    "Followers": {
                        "count": followers_count
                    }
                }
            }
            yield item


    def input_date_checker(self):

        start_date = raw_input("Enter Start Date (dd/mm/yyyy): ")
        date_regex = re.compile(r'(\d{2})[/.-](\d{2})[/.-]20(\d{2})$')
        start_date_group = re.search(date_regex, start_date)
        while not start_date_group:
            print("*************************************************")
            print("ERROR!!,Empty OR  please check Start Date format ")
            print("*************************************************")

            start_date = raw_input("Enter Start Date Again (dd/mm/yyyy): ")
            start_date_group = re.search(date_regex, start_date)
        start_date = start_date_group.group()
        start_epoch = (time.mktime(time.strptime(start_date, '%d/%m/%Y'))) - time.timezone

        end_date = raw_input("Enter End Date (dd/mm/yyyy): ")
        end_date_group = re.search(date_regex, end_date)
        while not end_date_group:
            print("*************************************************")
            print("ERROR, Empty OR please check End Date format ")
            print("*************************************************")
            end_date = raw_input("Enter End Date Again (dd/mm/yyyy): ")
            end_date_group = re.search(date_regex, end_date)
        end_date = end_date_group.group()
        end_epoch = (time.mktime(time.strptime(end_date, '%d/%m/%Y'))) - time.timezone

        if end_epoch < start_epoch:
            print("********************************************************************************")
            print("ERROR, Please end date must be either equal to start date or  ahead of start date")
            print ("Enter Start Date Again ")
            print("*********************************************************************************")

            self.input_date_checker()

        if end_epoch == start_epoch:
            ## add 24 hour
            end_epoch = start_epoch + 86400

        return start_epoch, end_epoch

    def input_hash_tag_checker(self):
        hashtag = raw_input("Enter Hash Tag# (shopping): ")
        group = re.search(r'^\w+(.*)', hashtag)

        while not group:
            print("***********************************************************************")
            print("ERROR!!!! HASH tag Format Error!! Starts with either Alpha or Numeric without #'")
            print("***********************************************************************")
            hashtag = raw_input("Enter Hash Tag Again# (shopping): ")
            group = re.search(r'^\w+(.*)', hashtag)

        return group.group()

    def input_min_followers_checker(self):

        followers = raw_input("Enter Minimum Followers (+ve numbers only): ")
        group = re.search(r'^[0-9]+$', followers)
        while not group:
            print("*****************************************************")
            print("ERROR!!!! Only +ve Integer!! please Check the format'")
            print("******************************************************")
            followers = raw_input("Enter Minimum Followers Again (+ve numbers only): ")
            group = re.search(r'^[0-9]+$', followers)

        return group.group()
