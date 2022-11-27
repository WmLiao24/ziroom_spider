# -*- coding: utf-8 -*-
import logging
import os
import sys
from urllib.parse import urljoin

import datetime
import requests
import scrapy

from ziroom.spiders.price_util import get_price_num_from_pos, data_path

logger = logging.getLogger(__name__)

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
isDebug = True if sys.gettrace() else False

from ziroom.items import ZiroomItem

class PriceMonitorSpider(scrapy.Spider):
    name = 'price_monitor'
    allowed_domains = ['ziroom.com']
    start_urls = [
        "https://www.ziroom.com/z/?p=x3&qwd=%E9%80%9A%E6%83%A0%E5%AE%B6%E5%9B%AD&isOpen=1",
        "https://www.ziroom.com/z/?p=x4&qwd=%E9%80%9A%E6%83%A0%E5%AE%B6%E5%9B%AD&isOpen=1"
    ]

    def parse(self, response, **kwargs):
        for item in response.css(".Z_list-box .item"):
            item_title = item.css(".title a::text").extract_first()
            logger.info("handle: %s", item_title)
            item_url = item.css(".title a::attr(href)").extract_first()
            item_id = item.css(".title a::attr(href)").re_first("\d+")
            item_desc = item.css(".desc div::text").extract_first()
            price_num_e = item.css(".price .num::attr(style)")
            underline_price_num_e = item.css(".underline_price .s_num::attr(style)")
            tip = item.css(".tip::text").extract_first()
            title_class = item.css(".title::attr(class)").extract_first()
            sign_status = None
            if "sign" in title_class:
                sign_status = "签约"
            elif "release" in title_class:
                sign_status = "待释放"
            elif "turn" in title_class:
                sign_status = "转"

            # 按日期和房间ID分组唯一，当日可以多次更新
            id = "%s%s"%(datetime.datetime.today().strftime("%Y%m%d"), item_id)
            yield ZiroomItem(id=id, item_url=item_url.strip('/'), item_id=item_id,
                             item_title=item_title, item_desc=item_desc,
                             tip=tip, sign_status=sign_status,
                             price=self.parse_price(price_num_e,background_size=20),
                             underline_price=self.parse_price(underline_price_num_e, background_size=15))

    def parse_price(self, ele, background_size):
        if len(ele) == 0:
            logger.warning("miss element!")
            return
        price_num_img_url = ele.re_first("(?<=url\()[^)]+")
        price_num_img_path = self.load_price_image(price_num_img_url)
        price_num_pos_list = ele.re("(?<=position: -)\d+")
        num = get_price_num_from_pos(price_num_img_path,
            background_size=background_size, price_num_pos_list=price_num_pos_list)
        return num

    def load_price_image(self, image_url):
        fname = os.path.split(image_url)[1]
        cache_file = data_path(fname)
        if os.path.exists(cache_file):
            logger.debug("load from cache: %s", fname)
        else:
            logger.info("save to: %s", fname)
            resp = requests.get(urljoin("http://", image_url))
            with open(cache_file, "wb") as f:
                f.write(resp.content)
        return cache_file
