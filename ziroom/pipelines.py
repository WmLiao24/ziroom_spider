# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
from select import select

from sqlalchemy.orm import Session

from ziroom.items import ZiroomItem
from ziroom.models import ZiroomRoomItem, ZiroomRoomItemLog, ZiroomAdjustPriceLog, Base, current_time
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

    def open_spider(self, spider):
        self.begin_time = current_time()
        logger.debug("begin at: %s", self.begin_time)

    def process_item(self, item, spider):
        if isinstance(item, ZiroomItem):
            session.merge(ZiroomRoomItemLog(**item, update_at=current_time()))
            session.commit()
        return item

    def close_spider(self, spider):
        end_time = current_time()
        logger.info("finish collect, cost: %s ms", end_time-self.begin_time)
        # 完成基本信息的变更
        try:
            items = ZiroomRoomItemLog.compare_old(session, self.begin_time)
            session.flush()
            session.commit()
        except Exception as e:
            logger.exception("compare old error: %s", str(e))
            session.rollback()
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
            session.rollback()

