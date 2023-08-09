import logging
logging.basicConfig(level=logging.DEBUG)

import unittest

from pyppeteer import launch

from ziroom import data_path
from ziroom.geetest_break import GeetestBreak
from ziroom.geetest_pyppeteer import GeetestBreakPyppeteer


class TestGeetestBreak(unittest.TestCase):

    def setUp(self):
        self.geetest_break = GeetestBreak(debug=True)

    def test_break(self):
        with open(data_path("geetest_bg.png"), "rb") as f:
            bg = f.read()
        with open(data_path("geetest_slice.png"), "rb") as f:
            slice = f.read()
        distance, track = self.geetest_break.get_mouse_trace_path(bg, slice, slice_name="geetest_result.png")
        print("track:", track)


class TestGeetestBreakPyppeteer(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.geetest_break_pyppeteer = GeetestBreakPyppeteer(debug=False)

    async def test_break_in_pyppetter(self):
        browser = await launch(headless=False, executablePath="C:\soft\Win_x64_706915_chrome-win\chrome.exe",
                               args=['--disable-infobars', '--window-size=1366,768', '--no-sandbox'])
        page = await browser.newPage()
        await page.setViewport({'width': 1368, 'height': 768})
        # 注册事件监听器
        await self.geetest_break_pyppeteer.register_page_listener(page)
        # 打开页面
        await page.goto('https://hot.ziroom.com/zrk-rent/valid?identity=Z%2BjHfITqQidYH3OqYrZhVg%3D%3D&return=http%3A%2F%2Fwww.ziroom.com%2Fz%2Fs100011%257C510100100037%257C100004-t100097%2F%3FisOpen%3D0')
        # 处理
        await self.geetest_break_pyppeteer.parse_valid_page(page)
        await browser.close()

