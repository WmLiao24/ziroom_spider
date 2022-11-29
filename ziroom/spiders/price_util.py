# -*- coding: utf-8 -*-
import json
import logging
import math
import os

import cv2
import ddddocr
import pytesseract
from PIL import Image

from ziroom import data_path

ocr = ddddocr.DdddOcr()
logger = logging.getLogger(__name__)


def get_pure_img(background_image_path: str):
    """二值化图片"""
    fname = os.path.split(background_image_path)[1]
    fname1, ext = os.path.splitext(fname)
    pure_image_path = data_path(fname1+"_pure"+ext)
    if os.path.exists(pure_image_path):
        return cv2.imread(background_image_path, cv2.IMREAD_UNCHANGED)

    # 自如的价格放到了alpha通道里，需要全部读取
    img = cv2.imread(background_image_path, cv2.IMREAD_UNCHANGED)
    _, _, _, a = cv2.split(img)
    # 二值化
    _, img = cv2.threshold(a, 150, 255, cv2.THRESH_BINARY)
    cv2.imwrite(pure_image_path, img)
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
    pure_image = get_pure_img(background_image_path)
    # 读取原始图像
    background_img = Image.fromarray(pure_image)
    size = background_img.size
    code1 = ocr.classification(background_img).strip()
    config = r"--oem 3 --psm 6 outputbase digits"
    code2 = pytesseract.image_to_string(background_img, config=config).strip()
    code = None
    if code1 and code1 == code2:
        # 100%正确
        code = code1
    elif isDebug:
        # 有问题，在debug模式里人工干预
        print("please verify: %s, rst: %s != %s"%(fname, code1, code2))
        while not code:
            index = input("type in 1:code1 / 2:code2 / 3:manual: ").strip()
            if index == "1":
                code = code1
                break
            elif index == "2":
                code = code2
                break
            elif index == "3":
                code = input("correct code: ").strip()
                break

    if not code:
        raise Exception("detect error, rst: %s != %s", code1, code2)
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
