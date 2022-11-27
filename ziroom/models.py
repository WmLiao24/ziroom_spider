import datetime
import logging
import time

import blinker
from sklearn.linear_model import LinearRegression
from sqlalchemy import Column, String, Integer, Date
from sqlalchemy.orm import declarative_base, Session

logger = logging.getLogger(__name__)
Base = declarative_base()

today = datetime.datetime.today()

after_online = blinker.Signal(doc="新上线, 参数: item")
after_release = blinker.Signal(doc="新释放, 参数: item")
after_adjust_price = blinker.Signal(doc="调价, 参数: adjust, item_log")
predict_adjust_nearly = blinker.Signal(doc="预测近期调价，参数：item, left_days, self.predict_adjust_price")

def current_time():
    return int(time.time()*1000)


class ZiroomRoomItemLog(Base):
    """自如房采集记录"""
    __tablename__ = "ziroom_room_item_log"
    id = Column(String(32), primary_key=True, comment="ID，房间ID+日期")
    item_id = Column(Integer, nullable=False, comment="房间ID")
    item_url = Column(String(255), nullable=False, comment="房间地址")
    item_title = Column(String(255), nullable=False, comment="标题")
    item_desc = Column(String(255), nullable=False, comment="房间描述")
    tip = Column(String(255), nullable=True, comment="优惠提示")
    sign_status = Column(String(255), nullable=True, comment="签约状态")
    direction = Column(String(255), nullable=True, comment="朝向")
    using_area = Column(String(255), nullable=True, comment="使用面积")
    house_type = Column(String(255), nullable=True, comment="户型")
    floor = Column(String(255), nullable=True, comment="楼层")
    sign_date_limit = Column(String(255), nullable=True, comment="签约时长")
    house_id = Column(String(20), nullable=True, comment="房屋号")
    room_id = Column(String(20), nullable=True, comment="房间号")
    inv_no = Column(String(20), nullable=True, comment="?")
    price = Column(Integer, nullable=True, comment="价格")
    underline_price = Column(Integer, nullable=True, comment="划线价格")
    create_at = Column(Integer, default=current_time, comment="创建时间")
    update_at = Column(Integer, nullable=True, comment="更新时间")

    def get_h5_url(self):
        return 'https://hot.ziroom.com/zrk_rent_cn/pages/detail/main?id=%s&house_id=%s&inv_no=%s&pageSource=homePage'%(
            self.room_id, self.house_id, self.inv_no
        )

    @classmethod
    def compare_old(cls, session, begin_time):
        # 比较历史记录
        results = session.query(ZiroomRoomItemLog, ZiroomRoomItem) \
                .outerjoin(ZiroomRoomItem, ZiroomRoomItemLog.item_id==ZiroomRoomItem.item_id) \
                .filter(ZiroomRoomItemLog.create_at >= begin_time)
        items = []
        for item_log, item in results:
            # 区分新增和修改，计算历史
            if item is None:
                item = ZiroomRoomItem.add_item_from_log(session, item_log)
            else:
                item.merge_item_and_log(session, item_log)
                session.merge(item)
            items.append(item)

        logger.debug("refresh items: %s", len(items))
        return items

    def __repr__(self):
        return '<ZiroomRoomItemLog %r>' % self.id


class ZiroomRoomItem(Base):
    """自如房间"""
    __tablename__ = "ziroom_room_item"
    item_id = Column(Integer, primary_key=True, comment="房间ID")
    item_url = Column(String(255), nullable=False, comment="房间地址")
    item_title = Column(String(255), nullable=False, comment="标题")
    item_desc = Column(String(255), nullable=False, comment="房间描述")
    tip = Column(String(255), nullable=True, comment="优惠提示")
    sign_status = Column(String(20), nullable=True, comment="签约状态(签约|待释放|转)")
    direction = Column(String(255), nullable=True, comment="朝向")
    using_area = Column(String(255), nullable=True, comment="使用面积")
    house_type = Column(String(255), nullable=True, comment="户型")
    floor = Column(String(255), nullable=True, comment="楼层")
    sign_date_limit = Column(String(255), nullable=True, comment="签约时长")
    house_id = Column(String(20), nullable=True, comment="房屋号")
    room_id = Column(String(20), nullable=True, comment="房间号")
    inv_no = Column(String(20), nullable=True, comment="?")
    price = Column(Integer, nullable=True, comment="价格")
    underline_price = Column(Integer, nullable=True, comment="划线价格")
    release_date = Column(Date, nullable=True, comment="释放时间")
    latest_adjust_price_date = Column(Date, nullable=True, comment="最后调价时间")
    predict_adjust_price_date = Column(Date, nullable=True, comment="预期调价时间")
    predict_adjust_price = Column(Integer, nullable=True, comment="预期调价")
    create_at = Column(Integer, default=current_time, comment="创建时间")
    update_at = Column(Integer, nullable=True, comment="更新时间")

    def get_h5_url(self):
        return 'https://hot.ziroom.com/zrk_rent_cn/pages/detail/main?id=%s&house_id=%s&inv_no=%s&pageSource=homePage'%(
            self.room_id, self.house_id, self.inv_no
        )

    @classmethod
    def add_item_from_log(cls, session:Session, item_log:ZiroomRoomItemLog):
        """新房间"""
        item = ZiroomRoomItem(
            item_id=item_log.item_id, item_url=item_log.item_url,
            item_title=item_log.item_title, item_desc=item_log.item_desc,
            tip=item_log.tip, sign_status=item_log.sign_status,
            price=item_log.price, underline_price=item_log.underline_price,
            direction=item_log.direction, using_area=item_log.using_area,
            house_type=item_log.house_type, floor=item_log.floor,
            sign_date_limit=item_log.sign_date_limit, house_id=item_log.house_id,
            room_id=item_log.room_id, inv_no=item_log.inv_no,
            update_at=current_time())
        session.add(item)

        # 在采集之前调价？保存调价记录
        if item.underline_price:
            ZiroomAdjustPriceLog.add_adjust_from_log(session, item_log, item)

        # 发送通知
        after_online.send(item)

        return item

    def merge_item_and_log(self, session, item_log:ZiroomRoomItemLog):
        """合并房间记录"""
        # 更新基本信息
        self.item_title = item_log.item_title
        self.item_desc = item_log.item_desc
        self.tip = item_log.tip
        self.underline_price = item_log.underline_price
        self.direction = item_log.direction
        self.using_area = item_log.using_area,
        self.house_type = item_log.house_type
        self.floor = item_log.floor,
        self.sign_date_limit = item_log.sign_date_limit
        self.house_id = item_log.house_id,
        self.room_id = item_log.room_id
        self.inv_no = item_log.inv_no,
        self.update_at = current_time()

        if self.price != item_log.price:
            # 生成调价记录
            self.price = item_log.price
            self.latest_adjust_price_date = today
            # 经过对比确定是产生了条件行为，记录日志
            adjust = ZiroomAdjustPriceLog.add_adjust_from_log(session, item_log, item=self, adjust_price_date=today)
            # 发送广播，通知已经调价
            after_adjust_price.send(adjust, item_log)
        if item_log.sign_status != self.sign_status and item_log.sign_status == "签约":
            # 更新签约时间
            self.release_date = today
            # 发送广播，通知已经释放
            after_release.send(self)

    def predict_next_adjust(self, session, between_days_model, price_model):
        """预测房间调价"""
        if not price_model and not price_model:
            logger.warning("miss models")
            return

        if price_model:
            next_price = self.predict_next_adjust_price(price_model)
            self.predict_adjust_price = int(next_price)

        if between_days_model:
            next_days = self.predict_next_adjust_between_days(between_days_model)
            if self.latest_adjust_price_date:
                # 上次调整时间 + between_days
                self.predict_adjust_price_date = self.latest_adjust_price_date + datetime.timedelta(days=next_days)
                left_days = self.predict_adjust_price_date - today
                if 0 <= left_days.total_seconds()/86400 <= 3:
                    # 预测时间比较临近，发送通知
                    predict_adjust_nearly.send(self, left_days=left_days, next_price=self.predict_adjust_price)
            else:
                # 没有记录？可能是新增
                self.predict_adjust_price_date = today + datetime.timedelta(days=next_days)
        self.update_at = current_time()
        session.merge(self)

    def predict_next_adjust_between_days(self, model):
        """预测房间调价间隔"""
        # 参数为定价和当前的价格
        params = [[self.underline_price or self.price, self.price]]
        next_between_days = model.predict(params)[0]
        logger.debug("params: %s next_between_days: %s", params, next_between_days)
        return next_between_days

    def predict_next_adjust_price(self, model):
        """预测房价调整"""
        # 参数为定价和当前的价格
        params = [[self.underline_price or self.price, self.price]]
        next_price = model.predict(params)[0]
        logger.debug("params: %s next_price: %s", params, next_price)
        return next_price

    def __repr__(self):
        return '<ZiroomRoomItem %r>' % self.item_id


class ZiroomAdjustPriceLog(Base):
    """自如房间调价记录"""
    __tablename__ = "ziroom_adjust_price_log"
    id = Column(Integer, autoincrement=True, primary_key=True, comment="ID")
    item_id = Column(Integer, nullable=False, comment="房间ID")
    old_price = Column(Integer, nullable=True, comment="旧价格")
    new_price = Column(Integer, nullable=True, comment="新价格")
    underline_price = Column(Integer, nullable=True, comment="划线价格")
    adjust_price_date = Column(Date, nullable=True, comment="调价时间")
    between_days = Column(Integer, nullable=True, comment="两次调整间隔")
    create_at = Column(Integer, default=current_time, comment="创建时间")

    @classmethod
    def add_adjust_from_log(cls, session: Session, item_log:ZiroomRoomItemLog, item:ZiroomRoomItem,
                            adjust_price_date=None):
        """生成调价记录"""
        # 调价的差距天数
        between_days = None

        # 如果本次采集日期就是调价日期
        if adjust_price_date:
            # 调取上一次调价记录，计算本次调价的差距天数
            prev_adjust = session.query(ZiroomAdjustPriceLog) \
                .filter(ZiroomAdjustPriceLog.item_id == item_log.item_id) \
                .order_by(ZiroomAdjustPriceLog.create_at.desc()) \
                .first()

            if prev_adjust:
                between_days = int((adjust_price_date - prev_adjust.adjust_price_date).total_seconds() / 86400)

        curr_adjust = ZiroomAdjustPriceLog(
            item_id=item_log.item_id,
            underline_price=item_log.underline_price,
            old_price=item.price,
            new_price=item_log.price,
            adjust_price_date=adjust_price_date,
            between_days=between_days,
        )
        session.add(curr_adjust)
        return curr_adjust

    @classmethod
    def refresh_predict_adjust_model(cls, session):
        """重新生成预测调价模型"""
        between_days_model = cls.refresh_predict_adjust_between_days_model(session)
        price_model = cls.refresh_predict_adjust_price_model(session)
        return between_days_model, price_model

    @classmethod
    def refresh_predict_adjust_between_days_model(cls, session):
        """生成调价时间模型"""
        results = session.query(ZiroomAdjustPriceLog) \
            .filter(ZiroomAdjustPriceLog.between_days.is_not(None)) \
            .all()
        if len(results) == 0:
            logger.warning("miss enough data!")
            return
        # 生成LR模型
        x_train = []
        y_train = []
        for result in results:
            x_train.append([result.underline_price, result.old_price])
            y_train.append(result.between_days)

        logger.debug("train between days model items: %s", len(x_train))

        model = LinearRegression()
        model.fit(x_train, y_train)
        return model

    @classmethod
    def refresh_predict_adjust_price_model(cls, session):
        """生成调价模型"""
        results = session.query(ZiroomAdjustPriceLog) \
            .filter(ZiroomAdjustPriceLog.old_price != ZiroomAdjustPriceLog.new_price) \
            .all()
        if len(results) == 0:
            logger.warning("miss enough data!")
            return
        # 生成LR模型
        x_train = []
        y_train = []
        for result in results:
            x_train.append([result.underline_price, result.old_price])
            y_train.append(result.new_price)

        logger.debug("train price model items: %s", len(x_train))

        model = LinearRegression()
        model.fit(x_train, y_train)
        return model

    def __repr__(self):
        return '<ZiroomAdjustPriceLog %r>' % self.item_id
