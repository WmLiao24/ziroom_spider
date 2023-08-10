import requests
import re

session = requests.session()

if __name__ == '__main__':
    # login page
    resp = session.get("http://192.168.1.1/loginUser.htm")
    m = re.search("sessionKey='(\d+)'", resp.text)
    if m:
        data = {
            "username": "user", "password": "asvksvbv", "sessionKey": m.group(1)
        }
        session.post("http://192.168.1.1/loginUser.htm", data)
        resp = session.get("http://192.168.1.1/devicemng_rebootinfo.htm")
        print(resp.status_code)
