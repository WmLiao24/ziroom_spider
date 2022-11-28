import base64
import hashlib
import hmac
import time
import urllib.parse

import requests


class DingDingNotifyUtil:

    def __init__(self, access_token, secret):
        self.access_token = access_token
        self.secret = secret

    def send_notify(self, title, msg):
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = '{}\n{}'.format(timestamp, self.secret)
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        requests.post("https://oapi.dingtalk.com/robot/send?access_token=%s&timestamp=%s&sign=%s"%(self.access_token, timestamp, sign), json={
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": msg
            }
        })
