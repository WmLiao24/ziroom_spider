# -*- coding: utf-8 -*-
import json
import logging
import math
import os

import pytesseract
from PIL import Image

from ziroom import data_path

logger = logging.getLogger(__name__)

def get_pure_img(background_image_path: str):
    """二值化图片"""
    fname = os.path.split(background_image_path)[1]
    fname1, ext = os.path.splitext(fname)
    pure_image_path = data_path(fname1+"_pure"+ext)
    if os.path.exists(pure_image_path):
        return Image.open(pure_image_path)

    # 自如的价格放到了alpha通道里，需要全部读取
    img = Image.open(background_image_path, 'r')
    assert img.mode == 'RGBA', "miss alpha channel"

    _, _, _, a = img.split()
    threshold = 150
    # 二值化
    filter_func = lambda x: 0 if x < threshold else 1
    img = a.point(filter_func, '1')
    img.save(pure_image_path)
    return img

def get_price_image_info(background_image_path:str):
    """获取价格图片信息"""
    fname = os.path.split(background_image_path)[1]
    fname1, ext = os.path.splitext(fname)
    info_path = data_path(fname1 + ".json")
    if os.path.exists(info_path):
        with open(info_path, "r") as f:
            return json.load(f)
    # 二值化图像
    background_img = get_pure_img(background_image_path)
    # 读取原始图像
    size = background_img.size
    config = r"--oem 3 --psm 6 outputbase digits"
    code = pytesseract.image_to_string(background_img, config=config).strip()

    if not code:
        raise Exception("detect error, rst: %s != %s", code)
    data = {
        "code": code,
        "weight": size[0],
        "height": size[1]
    }
    with open(info_path, "w") as f:
        json.dump(data, f)
    return data

def get_price_num_from_pos(background_image_path:str, background_size:int, price_num_pos_list:list):
    """获取价格"""
    info = get_price_image_info(background_image_path)
    num = 0
    n = len(price_num_pos_list)
    for i, price_num_pos in enumerate(price_num_pos_list):
        # 左侧位置在图中的什么位置
        pos = int(price_num_pos)
        pos_index = int(pos / background_size)
        parse_val = info["code"][pos_index]
        num += int(parse_val) * int(math.pow(10, n - i - 1))
    return num
