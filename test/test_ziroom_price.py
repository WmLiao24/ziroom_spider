import unittest

from sklearn.linear_model import LinearRegression

from ziroom.models import ZiroomRoomItemLog, ZiroomAdjustPriceLog, ZiroomRoomItem
from ziroom.spiders.price_util import *

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