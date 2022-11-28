# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
from select import select

import datetime
from sqlalchemy.orm import Session

from ziroom.dingding import DingDingNotifyUtil
from ziroom.items import ZiroomItem
from ziroom.models import ZiroomRoomItem, ZiroomRoomItemLog, ZiroomAdjustPriceLog, Base, current_time, \
    after_release, after_adjust_price, predict_adjust_nearly, after_online
from sqlalchemy import create_engine

from ziroom.spiders.price_util import data_path
import logging

logger = logging.getLogger(__name__)

engine = create_engine("sqlite+pysqlite:///"+data_path("all.db"), echo=True, future=True)
Base.metadata.create_all(engine)
session = Session(engine)

class ZiroomPipeline(object):

    def __init__(self):
        self.begin_time = None
        self.ding = None
        self.msgs = []

    def open_spider(self, spider):
        self.begin_time = current_time()
        logger.debug("begin at: %s", self.begin_time)
        if spider.settings.get("OPEN_DING_NOTIFY"):
            self.register_ding_notify(spider)

    def process_item(self, item, spider):
        if isinstance(item, ZiroomItem):
            session.merge(ZiroomRoomItemLog(**item, update_at=current_time()))
            session.commit()
        return item

    def close_spider(self, spider):
        end_time = current_time()
        logger.info("finish collect, cost: %s ms", end_time-self.begin_time)
        try:
            # 完成基本信息的变更
            items = []
            try:
                items = ZiroomRoomItemLog.compare_old(session, self.begin_time)
                # 日常统计信息
                self.msgs.append("<font color=\"#C8C8C8\">%s 共更新 %s 条记录</font>" % (datetime.datetime.today().strftime("%Y-%m-%d"), len(items)))
                session.flush()
                session.commit()
            except Exception as e:
                logger.exception("compare old error: %s", str(e))
                self.msgs.append("<font color=\"#FF0000\">比对过程发生异常</font>， %s" % str(e))
                session.rollback()

            if not items:
                return

            # 预测价格
            try:
                # 更新预测调价日期模型
                between_days_model, price_model = ZiroomAdjustPriceLog.refresh_predict_adjust_model(session)
                for item in items:
                    item.predict_next_adjust(session, between_days_model, price_model)
                session.flush()
                session.commit()
            except Exception as e:
                logger.exception("predict next adjust error: %s", str(e))
                self.msgs.append("<font color=\"#FF0000\">预测过程发生异常</font>， %s" % str(e))
                session.rollback()
        finally:
            self.send_ding_notify()

    def send_ding_notify(self):
        """发送信息"""
        try:
            if self.ding and self.msgs:
                self.ding.send_notify("  \n".join(self.msgs))
        except Exception as e:
            logger.exception("sending error: %s", str(e))

    def register_ding_notify(self, spider):
        self.ding = DingDingNotifyUtil(
            access_token=spider.settings.get("DING_ACCESS_TOKEN"), secret=spider.settings.get("DING_SECRET"))
        after_online.connect(self.handle_online)
        after_release.connect(self.handle_release)
        after_adjust_price.connect(self.handle_adjust_price)
        predict_adjust_nearly.connect(self.handle_predict_adjust_nearly)

    def handle_online(self, item, **_):
        """发送上线通知"""
        self.msgs.append("**上线了！** %s [web](%s)，[h5](%s)，%s %s"%(
            item.item_title, item.item_url, item.get_h5_url(), item.item_desc, item.price))

    def handle_release(self, item, **_):
        """发送释放通知"""
        self.msgs.append("**释放了！** %s [web](%s)，[h5](%s)，%s %s"%(
            item.item_title, item.item_url, item.get_h5_url(), item.item_desc, item.price))

    def handle_adjust_price(self, adjust, item_log, **_):
        """处理调价通知"""
        self.msgs.append("**调价了！** %s [web](%s)，[h5](%s)，从 %s 调到了 %s"%(
            item_log.item_title, item_log.item_url, item_log.get_h5_url(), adjust.old_price, adjust.new_price))

    def handle_predict_adjust_nearly(self, item, **_):
        """处理预期调价临近通知"""
        self.msgs.append("**关注一下！** [%s](%s) 现在价格 %s，预期 %s 会调价到 %s"%(
            item.item_title, item.item_url, item.price, item.predict_adjust_price_date, item.predict_adjust_price))

