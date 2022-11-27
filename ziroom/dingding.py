import requests

import time
import hmac
import hashlib
import base64
import urllib.parse


class DingDingNotifyUtil:

    def __init__(self, access_token, secret):
        self.access_token = access_token
        self.secret = secret
        import socket
        # 获取本机电脑名
        self.myname = socket.getfqdn(socket.gethostname())

    def send_notify(self, msg):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        requests.post("https://oapi.dingtalk.com/robot/send?access_token=%s&timestamp=%s&sign=%s"%(self.access_token, timestamp, sign), json={
            "msgtype": "markdown",
            "markdown": {
                "title": "Send by ZiroomSpider(%s):"%self.myname,
                "text": msg
            }
        })
