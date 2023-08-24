# -*- coding: utf-8 -*-

import logging
# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html
from urllib.parse import urljoin

import scrapy
from scrapy import signals
from sqlalchemy import select

from ziroom.gerapy_request import PyppeteerRequest
from ziroom.geetest_pyppeteer import GeetestBreakPyppeteer

logger = logging.getLogger(__name__)
valid_pattern = "https://hot.ziroom.com/zrk-rent/valid"
geetest_break_pyppeteer = GeetestBreakPyppeteer()

request_args = {
    'dont_filter': True,
    'pretend': True,
    'before_actions': geetest_break_pyppeteer.register_page_listener,
    'actions': geetest_break_pyppeteer.parse_valid_page
}


class ZiroomSpiderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    def __init__(self):
        self.exists_item_ids = None

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, dict or Item objects.
        from ziroom.items import ZiroomItem
        for i in result:
            # 判断是否需要继续访问明细，历史中没有？需要补全明细？
            if isinstance(i, ZiroomItem) and i["item_id"] not in self.exists_item_ids and i["crawl_step"]==1:
                logger.debug("ignore detail: %s", i["item_id"])
                yield scrapy.Request(url=urljoin("https://", i["item_url"]), callback=spider.parse_detail,
                             cb_kwargs={"item": i})
            else:
                yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request, dict
        # or Item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r
        # url = "https://hot.ziroom.com/zrk-rent/valid?identity=Z%2BjHfITqQidYH3OqYrZhVg%3D%3D&return=http%3A%2F%2Fwww.ziroom.com%2Fz%2Fs100011%257C510100100037%257C100004-t100097%2F%3FisOpen%3D0"
        # yield PyppeteerRequest(url, callback=spider.parse, **request_args)

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
        from ziroom import session
        from ziroom.models import ZiroomRoomItem
        self.exists_item_ids = set(session.execute(select(ZiroomRoomItem.item_id)).scalars().all())


class ZiroomDownloaderMiddleware(object):
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        request.meta['dont_filter'] = True
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.
        if response.url.startswith(valid_pattern) and not isinstance(request, PyppeteerRequest):
            return PyppeteerRequest(response.url, callback=request.callback, **request_args)

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
