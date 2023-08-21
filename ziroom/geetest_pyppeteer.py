import asyncio
import json
import logging
import random
import time
import os
from urllib.parse import parse_qs, urlparse, unquote_plus

from pyppeteer.network_manager import Response
from pyppeteer.page import Page

from ziroom import data_path, session, env
from ziroom.geetest_break import GeetestBreak
from ziroom.models import GeetestBreakLog

logger = logging.getLogger(__name__)
PATH = os.path.dirname(os.path.abspath(__file__))

class GeetestBreakPyppeteer(object):

    def __init__(self, debug=False):
        self.debug = debug
        self.geetest_break = GeetestBreak(debug=debug)
        # self.prepare_load_lock = asyncio.Semaphore(0)
        self.prepare_bg_lock = asyncio.Semaphore(0)
        self.prepare_slice_lock = asyncio.Semaphore(0)
        self.valid_result_lock = asyncio.Semaphore(0)

    @staticmethod
    def get_jsonp_data(body_text):
        # 解析jsonp请求
        start_pos = body_text.index("(") + 1
        end_pos = body_text.rindex(")")
        return json.loads(body_text[start_pos:end_pos])

    async def task_parse_load_data(self, resp: Response, page_params):
        """使用脚本提交时有用，暂时未使用"""
        try:
            logger.debug("task_parse_load_data")
            result = urlparse(resp.url)
            args = parse_qs(result[-2])
            page_params["captcha_id"] = args.get("captcha_id")[0]
            # challenge 失败后再次加载时没有这个参数
            if "challenge" in args:
                page_params["challenge"] = args.get("challenge")[0]
                logger.info("process load, captcha_id: %s, challenge: %s",
                            page_params["captcha_id"], page_params["challenge"])

            data = await resp.text()
            resp_data = GeetestBreakPyppeteer.get_jsonp_data(data)
            page_params["payload"] = resp_data['data']['payload']
            page_params["process_token"] = resp_data['data']['process_token']
            page_params["lot_number"] = resp_data['data']['lot_number']
            page_params["datetime"] = resp_data['data']["pow_detail"]["datetime"]
            page_params["ypos"] = resp_data["data"]["ypos"]
            page_params["bg_url"] = resp_data['data']['bg']
            page_params["slice_url"] = resp_data['data']['slice']
        except Exception as e:
            logger.exception(e)
        finally:
            self.prepare_load_lock.release()

    async def task_parse_verify(self, resp: Response, page_params):
        try:
            logger.debug("task_parse_verify")
            data = await resp.text()
            resp_data = GeetestBreakPyppeteer.get_jsonp_data(data)
            page_params["result"] = resp_data['data']['result']

            logger.debug("verify result: %s", resp_data['data']['result'])

            self.valid_result_lock.release()
        except Exception as e:
            logger.exception(e)

    async def task_parse_img(self, resp: Response, page_params):
        try:
            logger.debug("task_parse_img")
            data = await resp.buffer()
            if "/bg/" in resp.url:
                page_params["bg"] = data
                self.prepare_bg_lock.release()
            elif "/slice/" in resp.url:
                page_params["slice_url"] = resp.url
                page_params["slice"] = data
                self.prepare_slice_lock.release()
        except Exception as e:
            logger.exception(e)

    async def register_page_listener(self, page: Page):
        # 监听请求，获取必要的参数
        # 自定义一个内部参数，在page对象上传递
        page._page_params = {}
        try:
            def handle_response(resp: Response):
                # 注意，回调函数不能用async...，否则不会被调用，内部的异步函数只能用create_task
                try:
                    if self.debug:
                        logger.debug("parse_response: %s", resp.url)

                    page_params = page._page_params
                    # if resp.url.startswith('https://gcaptcha4.geetest.com/load'):
                    #     # 验证码加载JS
                    #     asyncio.create_task(self.task_parse_load_data(resp, page_params))
                    if resp.url.startswith("https://gcaptcha4.geetest.com/verify"):
                        # 验证JS
                        asyncio.create_task(self.task_parse_verify(resp, page_params))
                    elif resp.url.startswith('https://static.geetest.com') \
                            and resp.url.endswith(".png") \
                            and ("/bg/" in resp.url or "/slice/" in resp.url):
                        # 资源
                        asyncio.create_task(self.task_parse_img(resp, page_params))
                except Exception as e:
                    logger.exception(e)

            page.on('response', handle_response)
        except Exception as e:
            logger.exception(e)

    async def mock_mouse_opt_tracks(self, page: Page, tracks):
        try:
            # 增加鼠标显示
            # if self.debug:
                # await page.addScriptTag({"path": os.path.join(PATH, "mouse-helper.js")})
            btn_ele = await page.waitForSelector("div.geetest_btn", visible=True)
            slice_ele = await page.waitForSelector("div.geetest_slice", visible=True)
            # 操作鼠标实现
            logger.debug("mouse opt.")
            btn_box = await btn_ele.boundingBox()
            logger.debug("btn_box: %s", btn_box)
            slice_box = await slice_ele.boundingBox()
            logger.debug("slice_box: %s", slice_box)
            slice_half_width = slice_box["width"] / 2 + random.randint(-3, 3)
            logger.debug("slice_half_width: %s", slice_half_width)

            move_paths = []
            curr_x = slice_box["x"] + slice_box["width"] / 2
            curr_y = btn_box["y"] + btn_box["height"] / 2
            move_paths.append((curr_x, curr_y))
            await page.mouse.move(curr_x, curr_y)  # 鼠标移动
            # await btn.hover()  # 鼠标悬停元素上
            await page.mouse.down()  # 鼠标落下
            for x, y, t in tracks:
                curr_x += x
                curr_y += y
                move_paths.append((curr_x, curr_y))
                logger.debug("move to: %d, %d, wait: %d", curr_x, curr_y, t)
                await page.mouse.move(curr_x, curr_y, {'steps': t})  # 鼠标移动

            if self.debug:
                image_path = data_path("full.png")
                await page.screenshot({"path": image_path})
                self.geetest_break.draw_mouse_paths_to_image(image_path, move_paths)
                logger.info("save full image")
                await asyncio.sleep(10)

            await asyncio.sleep(random.random() + random.randint(1, 3))
            await page.mouse.up()  # 鼠标松开
            logger.debug("finish mouse opt.")
        except Exception as e:
            logger.exception(e)

    async def try_break_once(self, page: Page):
        try:
            # 等待页面加载完成
            # await self.prepare_load_lock.acquire()
            await self.prepare_bg_lock.acquire()
            await self.prepare_slice_lock.acquire()

            # 获取滑块的移动轨迹
            page_params = getattr(page, "_page_params", {})
            # 当前预测的图片
            slice_url = page_params["slice_url"]
            _, tracks = self.geetest_break.get_mouse_trace_path(
                bg=page_params["bg"], slice=page_params["slice"],
                slice_name=os.path.basename(slice_url))

            # 操作鼠标实现
            await self.mock_mouse_opt_tracks(page, tracks)

            # 等待验证接口返回
            await self.valid_result_lock.acquire()

            return {
                "slice_url": slice_url,
                "tracks": json.dumps(tracks),
                "result": page_params["result"]
            }
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(e)

    @staticmethod
    def get_redirect_to_url(page_url):
        result = urlparse(page_url)
        args = parse_qs(result[-2])
        return unquote_plus(args.get("return")[0])


    async def parse_valid_page(self, page: Page):
        """解析验证页面"""
        try:
            # 解析跳转目的地
            redirect_to_url = self.get_redirect_to_url(page.url)
            logger.info("redirect_to_url: %s", redirect_to_url)
            assert redirect_to_url, "解析跳转地址失败"

            # 最多尝试几次
            for i in range(env.int("PYPPETEER_TRY_TIMES")):
                try:
                    logger.info("try time: %d", i)
                    break_task: asyncio.Task = asyncio.create_task(self.try_break_once(page))

                    await asyncio.wait({break_task}, timeout=env.int("PYPPETEER_TRY_TIMEOUT", 180))
                    if break_task.done():
                        break_log = break_task.result()
                        session.add(GeetestBreakLog(**break_log))
                        session.commit()
                        if break_log["result"] == "success":
                            # 保存当前拖动记录
                            logger.info("success in %d times", i+1)
                            return
                    else:
                        break_task.cancel()
                except asyncio.CancelledError:
                    logger.error("break timeout, cancel opt")
            else:
                logger.error("break max times")
        except Exception as e:
            logger.exception(e)
