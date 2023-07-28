import unittest

from sklearn.linear_model import LinearRegression

from ziroom.dingding import DingDingNotifyUtil
from ziroom.models import ZiroomRoomItemLog, ZiroomAdjustPriceLog, ZiroomRoomItem, ZiroomPredictPriceLog
from ziroom.spiders.price_util import *
from datetime import datetime
import time

logging.basicConfig(level=logging.DEBUG)

class ZiroomSpiderTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_pure_img(self):
        print(get_pure_img(data_path("a8a37e8b760bc3538c37b93d60043cfc.png")))
        print(get_pure_img(data_path("img_pricenumber_list_grey.png")))
        print(get_pure_img(data_path("img_pricenumber_list_red.png")))

    def test_get_price_image_info(self):
        info = get_price_image_info(data_path("a8a37e8b760bc3538c37b93d60043cfc.png"))
        print(info)

    def test_get_price_num_from_pos1(self):
        num = get_price_num_from_pos(
            data_path("a8a37e8b760bc3538c37b93d60043cfc.png"),
            background_size=20, price_num_pos_list=[21,42,171,192])
        print(num)

    def test_get_price_num_from_pos2(self):
        num = get_price_num_from_pos(
            data_path("img_pricenumber_list_red.png"),
            background_size=20, price_num_pos_list=[0, 20, 60, 80, 100, 140])
        print(num)

    def test_get_price_num_from_pos3(self):
        price = get_price_num_from_pos(
            data_path("img_pricenumber_list_grey.png"),
            background_size=15, price_num_pos_list=[45, 60, 90, 120])
        print(price)

    def test_pytesseract(self):
        import pytesseract
        config = r"--oem 3 --psm 6 outputbase digits"
        c = pytesseract.image_to_string(data_path("pure_a8a37e8b760bc3538c37b93d60043cfc.png"), config=config)
        print(c)
        c = pytesseract.image_to_string(data_path("pure_img_pricenumber_list_red.png"), config=config)
        print(c)
        c = pytesseract.image_to_string(data_path("pure_img_pricenumber_list_grey.png"), config=config)
        print(c)

    def test_ddddocr(self):
        import ddddocr
        ocr = ddddocr.DdddOcr()
        c = ocr.classification(Image.open(data_path("pure_a8a37e8b760bc3538c37b93d60043cfc.png")))
        print(c)
        c = ocr.classification(Image.open(data_path("pure_img_pricenumber_list_red.png")))
        print(c)
        c = ocr.classification(Image.open(data_path("pure_img_pricenumber_list_grey.png")))
        print(c)

    def test_compare_old(self):
        from ziroom.pipelines import session
        ZiroomRoomItemLog.compare_old(session, begin_time=0)

    def test_refresh_predict_adjust_model(self):
        from ziroom.pipelines import session
        between_days_model, price_model = ZiroomAdjustPriceLog.refresh_predict_adjust_model(session)
        from ziroom.pipelines import session
        for item in session.query(ZiroomRoomItem):
            item.predict_next_adjust(session, between_days_model, price_model)
        session.rollback()

    def test_train_predict(self):
        x_train = [
            [4000, 3860],
            [3500, 3400],
        ]
        days_y_train = [
            15, 12
        ]
        price_y_train = [
            300, 250
        ]
        between_days_model = LinearRegression()
        between_days_model.fit(x_train, days_y_train)
        print(between_days_model.predict([[3860, 3860]])[0])
        price_model = LinearRegression()
        price_model.fit(x_train, price_y_train)
        print(price_model.predict([[3860, 3860]])[0])

        from ziroom.pipelines import session
        for item in session.query(ZiroomRoomItem):
            item.predict_next_adjust(session, between_days_model, price_model)
        session.rollback()

    def test_send_ding_notify(self):
        from configparser import ConfigParser

        _other_config_path = data_path("other.cfg")
        _parser = ConfigParser()
        with open(_other_config_path, "r", encoding="utf8") as f:
            _parser.read_file(f)
        # 钉钉群消息
        ding = DingDingNotifyUtil(_parser.get("ding_notify", "access_token"), _parser.get("ding_notify", "secret"))
        ding.send_notify("**测试** [百度](https://www.baidu.com)  \n<font color=\"#FF0000\">警告</font> 错误发生了")

    def test_signal(self):
        import blinker
        s1 = blinker.Signal()
        s1.connect(self.handle_signal1)
        # s1.send(self, "abc")
        s1.send(self, param1="abc")
        s1.send(self, param1="abc", param2="ddd")

    def handle_signal1(self, sender, **params):
        print(sender, params.get("param1"))

    def test_handle_predict_log(self):
        """补齐预测日志"""
        import re
        log_pattern = re.compile("^.*\('([^']+)', (\d+), (\d+), (\d+)\)$")
        from ziroom.pipelines import session
        with open("../logs/update_predict_log_2023-7-20.log/update_predict_log_2023-7-20.log") as f:
            for i, row in enumerate(f):
                m = log_pattern.match(row.strip())
                if m:
                    predict_adjust_price_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                    predict_adjust_price = int(m.group(2))
                    create_at = int(m.group(3))
                    item_id = int(m.group(4))
                    price = None

                    # 从调价记录中找到上一条记录
                    prev_adjust = session.query(ZiroomAdjustPriceLog.new_price, ZiroomAdjustPriceLog.old_price)\
                        .filter(ZiroomAdjustPriceLog.item_id==item_id, ZiroomAdjustPriceLog.create_at <= create_at) \
                        .order_by(ZiroomAdjustPriceLog.create_at.desc()) \
                        .first()
                    if prev_adjust is not None:
                        price = prev_adjust.new_price or prev_adjust.old_price

                    log = ZiroomPredictPriceLog(
                        item_id=item_id, price=price, predict_adjust_price_date=predict_adjust_price_date,
                        predict_adjust_price=predict_adjust_price, create_at=create_at
                    )
                    session.add(log)
                if (i+1) % 100 == 0:
                    session.commit()
            session.commit()
