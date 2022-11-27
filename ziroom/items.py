# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class ZiroomItem(scrapy.Item):
    # define the fields for your item here like:
    id = scrapy.Field()
    item_url = scrapy.Field()
    item_id = scrapy.Field()
    item_title = scrapy.Field()
    item_desc = scrapy.Field()
    price = scrapy.Field()
    underline_price = scrapy.Field()
    tip = scrapy.Field()
    sign_status = scrapy.Field()

