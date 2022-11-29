# -*- coding: utf-8 -*-
import datetime
import logging
import os
from urllib.parse import urljoin

import requests
import scrapy

from ziroom import data_path
from ziroom.spiders.price_util import get_price_num_from_pos

logger = logging.getLogger(__name__)


from ziroom.items import ZiroomItem

class PriceMonitorSpider(scrapy.Spider):
    name = 'price_monitor'
    allowed_domains = ['ziroom.com']
    start_urls = [
        "https://www.ziroom.com/z/?p=x3&qwd=%E9%80%9A%E6%83%A0%E5%AE%B6%E5%9B%AD&isOpen=1",
        "https://www.ziroom.com/z/?p=x4&qwd=%E9%80%9A%E6%83%A0%E5%AE%B6%E5%9B%AD&isOpen=1"
        "https://www.ziroom.com/z/z1/?p=a3-x4&qwd=%E5%A4%A7%E6%9C%9B%E8%B7%AF&isOpen=1",
    ]

    def parse(self, response, **kwargs):
        # 检测是否有下一页
        next_url = response.css(".Z_pages a.next::attr(href)").extract_first()
        if next_url:
            yield scrapy.Request(url=urljoin("https://", next_url), callback=self.parse)

        for item in response.css(".Z_list-box .item"):
            item_title = item.css(".title a::text").extract_first()
            logger.info("handle: %s", item_title)
            item_url = item.css(".title a::attr(href)").extract_first()
            # 忽略公寓
            if not "/x/" in item_url:
                continue
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
            yield ZiroomItem(crawl_step=1, id=id, item_url=urljoin("https://", item_url), item_id=item_id,
                             item_title=item_title, item_desc=item_desc,
                             tip=tip, sign_status=sign_status,
                             price=self.parse_price(price_num_e,background_size=20),
                             underline_price=self.parse_price(underline_price_num_e, background_size=15))

    def parse_detail(self, response, **data):
        """处理详情页"""
        response.css("head script::text")
        house_id = response.css("script::text").re_first('(?<=house_id":")[^"]+')
        room_id = response.css("script::text").re_first('(?<=room_id":")[^"]+')
        inv_no = response.css("script::text").re_first('(?<=invNo":")[^"]+')
        home_info_ele = response.css(".Z_home_info .Z_home_b")
        using_area = home_info_ele.css("dl:contains(使用面积) dd::text").extract_first()
        direction = home_info_ele.css("dl:contains(朝向) dd::text").extract_first()
        house_type = home_info_ele.css("dl:contains(户型) dd::text").extract_first()
        floor = response.css(".Z_home_info .Z_home_o li:contains(楼层) .va::text").extract_first()
        sign_date_limit = response.css(".jiance .info_label:contains(签约时长)+.info_value::text").extract_first()
        item:ZiroomItem = data["item"]
        item.update(crawl_step=2, house_id=house_id, room_id=room_id, inv_no=inv_no,
                         using_area=using_area, direction=direction, house_type=house_type,
                         sign_date_limit=sign_date_limit, floor=floor)
        yield item

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
