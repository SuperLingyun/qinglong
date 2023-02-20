from requests import get, post, put, packages
import requests
from re import findall
from os.path import exists
import json
import os
import sys
packages.urllib3.disable_warnings()

"""
cron 57 5,17 * * *
"""

def printf(text):
    print(text)
    sys.stdout.flush()

def load_send():
    global send
    cur_path = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(cur_path)
    if os.path.exists(cur_path + "/sendNotify.py"):
        try:
            from sendNotify import send
        except:
            send=False
            printf("加载通知服务失败~")
    else:
        send=False
        printf("加载通知服务失败~")
load_send()


def getcookie(key):    
    url = os.environ.get("Rabbiturl")
    RabbitToken=os.environ.get("RabbitToken")
    payload = json.dumps({
      "wsck": key,
      "RabbitToken": RabbitToken
    })
    headers = {
      'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload).json()
    
    try:
        if response["success"]:
            cookie = response['data']['appck']       
            return cookie
        else:
            return ""
    except:
        printf("Error:"+str(response))
        return "Error"


def subcookie(pt_pin, cookie, token ,envtype):
    if envtype=="v4":
        sh = "/jd/config/config.sh"
        with open(sh, "r", encoding="utf-8") as read:
            configs = read.readlines()
        cknums = []
        for config in configs:
            cknum = findall(r'(?<=Cookie)[\d]+(?==")', config)
            if cknum != []:
                m = configs.index(config)
                cknums.append(cknum[0])
                if pt_pin in config:
                    configs[m] = f'Cookie{cknum[0]}="{cookie}"\n'
                    printf(f"更新cookie成功！pt_pin：{pt_pin}")
                    break
            elif "第二区域" in config:
                newcknum = int(cknums[-1]) + 1
                configs.insert(m + 1, f'Cookie{newcknum}="{cookie}"\n')
                printf(f"新增cookie成功！pt_pin：{pt_pin}")
                break
        with open(sh, "w", encoding="utf-8") as write:
            write.write("".join(configs))
    else:        
        if token!="":
            url = 'http://127.0.0.1:5600/api/envs'
            headers = {'Authorization': f'Bearer {token}'}
            body = {
                'searchValue': pt_pin,
                'Authorization': f'Bearer {token}'
            }
            datas = get(url, params=body, headers=headers).json()['data']            
            old = False
            isline=True
            for data in datas:
                if "pt_key" in data['value']:
                    try:
                        body = {"name": "JD_COOKIE", "value": cookie, "_id": data['_id']}
                    except:    
                        body = {"name": "JD_COOKIE", "value": cookie, "id": data['id']}
                        isline=False
                    old = True
                    break
            if old:
                put(url, json=body, headers=headers)
                url = 'http://127.0.0.1:5600/api/envs/enable'
                if isline:
                    body = [body['_id']]
                else:
                    body = [body['id']]
                put(url, json=body, headers=headers)
                printf(f"更新并启用cookie成功！pt_pin：{pt_pin}")
            else:
                body = [{"value": cookie, "name": "JD_COOKIE"}]
                post(url, json=body, headers=headers)
                printf(f"新增cookie成功！pt_pin：{pt_pin}")
def main():
    printf("版本: 20230210 V2")
    printf("说明1: 经测试转换后CK有效期是24小时，建议一天执行2次")
    printf("说明2: 扫码后的wskey不能用以前的WSKEY转换脚本转换")
    printf("===============开始转换==============")
    envtype=""
    config=""
    if os.path.exists("/ql/config/auth.json"):
        envtype="ql"
        config="/ql/config/auth.json"
    
    if os.path.exists("/ql/data/config/auth.json"):
        config="/ql/data/config/auth.json"
        envtype="newql"
        
    if os.path.exists("/jd/config/config.sh"):
        config="/jd/config/config.sh"
        envtype="v4" 
        
    if config=="":
        printf(f"无法判断使用环境，退出脚本!")
        return 
        
    if os.environ.get("Rabbiturl")=="":
        printf('没有配置Rabbiturl变量，例子: export Rabbiturl="http://192.168.1.23:6001/api/wsck"')
        return 
    
    if os.environ.get("RabbitToken")=="":
        printf('没有配置RabbitToken变量,填入兔子Token，例子: export RabbitToken="xxxxxxxxxxxxxxxx"')
        return
    
    with open(config, "r", encoding="utf-8") as f1:
        token = json.load(f1)['token']
    url = 'http://127.0.0.1:5600/api/envs'
    headers = {'Authorization': f'Bearer {token}'}
    body = {
        'searchValue': 'JD_R_WSCK',
        'Authorization': f'Bearer {token}'
    }
    datas = get(url, params=body, headers=headers).json()['data']
    for data in datas:
        key = data['value']
        pin = key.split(";")[0].split("=")[1]
        for num in range(0,5):
            cookie = getcookie(key)
            if cookie!="" and cookie!="Error":
                break
            else:
                printf(f"pin为{pin}的wskey转换失败，重试....")        
        
        if "app_open" in cookie:
            #printf("转换成功:"cookie)
            subcookie(pin, cookie, token, envtype)
        else:            
            message = f"pin为{pin}的wskey可能过期了！"
            printf(message)
            send("转换失败通知",message)


if __name__ == '__main__':
    main()
