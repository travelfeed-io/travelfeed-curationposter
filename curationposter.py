#!/usr/bin/python
# -*- coding: utf8 -*-

import json
import logging
import os
import re
from datetime import date, datetime, timedelta

import markdown
import pycountry
import sqlalchemy as db
from bs4 import BeautifulSoup
from markdown import markdown

from beem import Steem
from beem.nodelist import NodeList

walletpw = os.environ.get('UNLOCK')

logger = logging.getLogger(__name__)
logging.basicConfig(filename="curationposter.log", format='%(asctime)s %(levelname)s: %(message)s',
                    level=logging.INFO)  # Log to file: filename=logpath


with open('post_templates.json', encoding='utf-8') as json_file:
    template = json.load(json_file)


def post_to_steem(title, body, permlink, app, tags, beneficiaries):
    node_list = ['https://steemd.minnowsupportproject.org', 'https://rpc.usesteem.com', 'https://anyx.io',
                 'https://api.steemit.com', 'https://steemd.privex.io']
    steem = Steem(node=node_list)
    steem.wallet.unlock(walletpw)
    steem.post(title, body, author="travelfeed", permlink=permlink, json_metadata=None,
               community="travelfeed", app=app, tags=tags, beneficiaries=beneficiaries, parse_body=True)


def query_db(country_codes, tag, db_url):
    """
    Query the database for posts to be featured
    """
    engine = db.create_engine(
        db_url)
    connection = engine.connect()
    metadata = db.MetaData()
    hive_posts_cache = db.Table(
        'hive_posts_cache', metadata, autoload=True, autoload_with=engine)
    hive_post_tags = db.Table(
        'hive_post_tags', metadata, autoload=True, autoload_with=engine)
    created_after = datetime.utcnow()-timedelta(days=7)
    if country_codes != None:
        dayquery = hive_posts_cache.columns.country_code.in_(country_codes)
    else:
        # For Wednesday and Satuday round-up query by tag
        dayquery = hive_posts_cache.columns.post_id.in_(db.select(
            [hive_post_tags.columns.post_id]).where(hive_post_tags.columns.tag == tag))
    query = db.select([hive_posts_cache.columns.author, hive_posts_cache.columns.permlink, hive_posts_cache.columns.title, hive_posts_cache.columns.preview, hive_posts_cache.columns.img_url, hive_posts_cache.columns.country_code, hive_posts_cache.columns.subdivision, hive_posts_cache.columns.json]).where(db.and_(hive_posts_cache.columns.is_travelfeed ==
                                                                                                                                                                                                                                                                                                                          True, hive_posts_cache.columns.author != "travelfeed", dayquery, hive_posts_cache.columns.depth == 0, hive_posts_cache.columns.curation_score >= 3000, hive_posts_cache.columns.created_at > datetime(created_after.year, created_after.month, created_after.day))).order_by(hive_posts_cache.columns.curation_score.desc(), hive_posts_cache.columns.total_votes.desc())
    ResultProxy = connection.execute(query)
    ResultSet = ResultProxy.fetchall()
    return ResultSet


def get_post():
    today = datetime.utcnow()
    todate = today.date()
    weekday = todate.weekday()
    if weekday == 4:
        weekday = 5
    weekssincestart = str(
        abs((date(2018, 2, 19) - date.today()).days/7)).split('.')[0]
    post = template['post']
    dailytheme = post[str(weekday)]
    title = dailytheme['title']+" - Weekly Round-Up #"+weekssincestart
    tag = dailytheme['tag']
    tags = ["travelfeed", "travel", "fundition-81n9hwooj", "palnet", tag,
            "travelfeeddaily", "neoxian"]
    app = post['app']
    country_codes = dailytheme.get('country_codes', None)
    featured_posts = query_db(country_codes, tag, post['database_connection'])
    authorlist = []
    featured_post_text = ""
    selected_featured_posts = []
    count = 0
    authorcandidateslist = []
    for fp in featured_posts:
        try:
            data = json.loads(fp[7])
            if data['app'].split('/')[0] == 'travelfeed' and fp[0] not in authorcandidateslist and count < 3:
                authorcandidateslist += [fp[0]]
                count += 1
                selected_featured_posts += [fp]
        except Exception as e:
            print(e)
            continue
    for fp in selected_featured_posts:
        fp_author = fp[0]
        authorlist += [fp_author]
        fp_permlink = fp[1]
        fp_title = fp[2]
        caption_regex = r'<h.>.*</h.>'
        link_regex = r'/(?:https?|ftp):\/\/[\n\S]+/g'
        image_regex = r'''(https?:\/\/(?:[-a-zA-Z0-9._]*[-a-zA-Z0-9])(?::\d{2,5})?(?:[/?#](?:[^\s\"'<>\][()]*[^\s\"'<>\][().,])?(?:(?:\.(?:tiff?|jpe?g|png|svg|ico)|ipfs\/[a-z\d]{40,}))))'''
        fp_preview = re.sub(caption_regex, '', markdown(fp[3]))
        fp_preview = BeautifulSoup(
            fp_preview, features="html.parser").get_text()
        fp_preview = re.sub(link_regex, '', fp_preview)
        fp_preview = re.sub(image_regex, '', fp_preview)
        fp_preview = fp_preview[:350]+"[...]"
        fp_img_url = fp[4]
        fp_location = ""
        if weekday != 2 and weekday != 5:
            fp_country = pycountry.countries.get(alpha_2=fp[5].upper()).name
            fp_subdivision = fp[6]
            fp_location = '<p>📍<em>'+fp_country + \
                '</em></p>'
            if fp_subdivision != None:
                fp_location = '<p>📍<em>'+fp_subdivision+', '+fp_country + \
                    '</em></p>'
        featured_post_text += '<center><h4>'+fp_title+' <em> by <a href="https://travelfeed.io/@'+fp_author+'">@'+fp_author+'</a></em></h4>'+fp_location+'</center><blockquote><p>'+fp_preview+'</p></blockquote><center><a href="https://travelfeed.io/@' + \
            fp_author+'/'+fp_permlink+'"><img src="'+fp_img_url + \
            '" /></a></center><hr/>'
    body = post['header'].format(dailytheme['title']) + dailytheme['body'] + \
        post['subheader'].format(dailytheme['title']) + \
        featured_post_text + post['postsfooter'] + post['footer']
    if selected_featured_posts == []:
        body = post['header'].format(dailytheme['title'])+post['nopoststext'].format(
            dailytheme['title'], dailytheme['title']) + post['footer']
        logger.debug("No posts for topic")
    beneficiaries = []
    # remove duplicates, oder alphabetically
    authorlist = sorted(list(dict.fromkeys(authorlist)))
    for a in authorlist:
        beneficiaries += {'account': a, 'weight': 1300},
    permlink = dailytheme['title'].lower().replace(
        ', ', '-').replace(' & ', '-').replace(' ', '-')+"-weekly-round-up-"+weekssincestart
    # logger.info("title: "+title)
    # logger.info("tags: "+str(tags))
    # logger.info("body: "+body)
    # logger.info("beneficiaries:"+str(beneficiaries))
    post_to_steem(title,
                  body, permlink, app, tags, beneficiaries)


if __name__ == '__main__':
    get_post()
