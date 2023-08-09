import logging
import random
from pathlib import Path

import cv2
import itertools
import numpy as np

from ziroom import data_path

logger = logging.getLogger(__name__)


class GeetestBreak(object):

    def __init__(self, debug=False):
        self.debug = debug

    def get_mouse_trace_path(self, bg, slice, slice_name, failed_positions=None):
        bg_img = cv2.imdecode(np.frombuffer(bg, dtype=np.uint8), 1)
        slice_img = cv2.imdecode(np.frombuffer(slice, dtype=np.uint8), 1)

        position = self.try_get_slice_position(bg_img, slice_img, failed_positions)
        logger.debug("position: %s", position)

        track = self.get_slide_track(distance=position[0])
        logger.debug("track: %d", len(track))
        # 测试使用
        if self.debug:
            slice_y = int(position[1] + slice_img.shape[0] / 2)
            move_path = self.track_to_move_paths(slice_y, track)
            self.save_result_image(bg_img, slice_img, position, move_path, slice_name)
        return position[0], track

    def try_get_slice_position(self, bg_img, slice_img, failed_positions):
        # 制作一个掩码图
        mask = None
        if failed_positions:
            mask = np.ones(bg_img.shape[:2])
            slice_height, slice_width = slice_img.shape[:2]
            # 失败的尝试抹上
            for x, y in failed_positions:
                mask[y : y+slice_height, x : x+slice_width] = 0

        return self.get_slice_position(bg_img, slice_img, mask)

    @staticmethod
    def track_to_move_paths(slice_y, track):
        move_path = []
        curr_x = 0
        curr_y = slice_y
        move_path.append((curr_x, curr_y))
        for x, y, _ in track:
            curr_x += x
            curr_y += y
            move_path.append((curr_x, curr_y))
        return move_path

    def get_slice_position(self, bg_img, slice_img, mask=None):
        """
        :param bg: 背景图片二进制
        :param slice: 缺口图图片二进制
        :return: 缺口位置
        """
        # 读取图片
        slice_gray = cv2.cvtColor(slice_img, cv2.COLOR_RGB2BGR)

        # 金字塔均值漂移
        bg_shift = cv2.pyrMeanShiftFiltering(bg_img, 5, 50)

        # 边缘检测
        slice_gray = cv2.Canny(slice_gray, 255, 255)
        bg_gray = cv2.Canny(bg_shift, 255, 255)

        # 目标匹配
        result = cv2.matchTemplate(bg_gray, slice_gray, cv2.TM_CCOEFF_NORMED, mask)
        # 解析匹配结果
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # 左上角坐标
        return max_loc

    def save_result_image(self, bg_img, slice_img, position, track, slice_name=None):
        # 需要绘制的方框高度和宽度
        slice_height, slice_width = slice_img.shape[:2]
        # 矩形左上角点位置
        x, y = position
        # 矩形右下角点位置
        _x, _y = x + slice_width, y + slice_height
        # 绘制矩形
        cv2.rectangle(bg_img, (x, y), (_x, _y), (0, 0, 255), 2)
        # 绘制路径
        self.draw_mouse_paths(bg_img, track)

        # 保存缺口识别结果到背景图
        save_path = Path(data_path(slice_name)).resolve()
        save_path = save_path.parent / f"{save_path.stem}.{x}{save_path.suffix}"
        save_path = save_path.__str__()
        logger.info("save to: %s", save_path)
        cv2.imwrite(save_path, bg_img)

    def get_slide_track(self, distance):
        """
        根据滑动距离生成滑动轨迹，使用随机方法
        :param distance: 需要滑动的距离
        :return: 滑动轨迹<type 'list'>: [[x,y,t], ...]
            x: 已滑动的横向距离
            y: 已滑动的纵向距离, 除起点外, 均为0
            t: 滑动过程消耗的时间, 单位: 毫秒
        """
        if not isinstance(distance, int) or distance < 0:
            raise ValueError(f"distance类型必须是大于等于0的整数: distance: {distance}, type: {type(distance)}")
        # 初始化轨迹列表
        slide_track = []
        # 共记录count次滑块位置信息
        count = 30 + int(distance / 2)
        # 初始化滑动时间
        t = random.randint(50, 100)
        # 记录上一次滑动的距离
        _x = 0
        _y = 0
        for i in range(count):
            # 已滑动的横向距离
            x = round(self.__ease_out_expo(i / count) * distance)
            # 滑动过程消耗的时间
            t = random.randint(1, 3)
            if x == _x:
                continue
            _y = random.randint(-3, 3)
            slide_track.append([x - _x, _y, t])
            _x = x
        return slide_track

    def __ease_out_expo(self, x):
        if x == 1:
            return 1
        else:
            return 1 - pow(2, -10 * x)

    def draw_mouse_paths(self, img, move_paths):
        green = (0, 255, 0)
        red = (0, 0, 255)
        path_arr = np.array(move_paths, dtype=np.int32).tolist()
        for start_pos, end_pos in self.pairwise(path_arr):
            cv2.line(img, start_pos, end_pos, green if end_pos[0]>start_pos[0] else red, 2)

    def draw_mouse_paths_to_image(self, image_path, move_paths):
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        self.draw_mouse_paths(img, move_paths)
        cv2.imwrite(image_path, img)

    @staticmethod
    def pairwise(iterable):
        "s -> (s0,s1), (s1,s2), (s2, s3), ..."
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)