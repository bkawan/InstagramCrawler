# InstagramCrawler


Steps
1. Create a scrapy crawler that uses selenium and get the posts that match the input criteria. For this, the script will go to url https://www.instagram.com/explore/tags/shopping/ (the last word in the url is the hashtag), scroll down to Most Recent and get all posts that matches the given date.
2. Pull all export data points by going to post page and bio page of instagram user who posted the media. Save the data points to json file.

Create a script that aggregates all the posts on Instagram in a specific day that use a Hashtag. User should input a hashtag. It should then run for as long as it needs, and put all the posts with the specific hashtag (their link and a list of the other hashtags used) posted on that specific date. It should also be able to list the account tagged in the post. It should also allow me to filter what posts are exported by follower size. For example, I want all posts with the hashtag #shopping that were posted by people with a following of over 40,000 followers Doesn't need to look good. Just work.

Technical Description
Use scrapy & selenium.
Inputs: Date range (i.e. start_date & end_date), Hashtag, min_follower
Exports: Unique identifier for influencer, link to the post, influencer handle, influencer follower #, post likes, comments, engagement #, other hashtags in the post, other account tags, link in bio
Export file format: json


**P.S. Crawling is sometimes illegal. Please check the official Terms Of Service. :-)

