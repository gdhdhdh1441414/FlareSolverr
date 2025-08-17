# -*- coding: UTF-8 -*- 
import time
import re
import os
import sys
import json
import subprocess
from datetime import datetime

#subprocess.Popen(['sudo', 'python', 'src/flaresolverr.py'])

# 睡眠 20 秒以确保 flaresolverr.py 已经启动
time.sleep(36)

#判断代理有没有用
os.system("echo 代理ip:  && curl --proxy 127.0.0.1:1087 ifconfig.me")

# 使用 subprocess 模块调用 curl 命令，并捕获命令输出结果
curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + sys.argv[1] + "\",\"maxTimeout\": 60000, \"proxy\": { \"url\": \"http://127.0.0.1:1087\" }}'"
#curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + sys.argv[1] + "\",\"maxTimeout\": 60000}'"

result = subprocess.check_output(curl_cmd, shell=True)


# 解析 JSON 数据
data = json.loads(result.decode('utf-8'))
response = data.get("solution", {}).get("response")
print(response)  # 输出 response 数据



os.system("pkill chrome; pkill chromedriver")











"""
# -*- coding: UTF-8 -*- 
import time
import re
import os
import sys
import json
import subprocess
from datetime import datetime

#subprocess.Popen(['sudo', 'python', 'src/flaresolverr.py'])

# 睡眠 40 秒以确保 flaresolverr.py 已经启动
time.sleep(46)

#判断代理有没有用
os.system("curl --proxy 127.0.0.1:1085 https://proapi.115.com/app/uploadinfo")

# 使用 subprocess 模块调用 curl 命令，并捕获命令输出结果
curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + sys.argv[1] + "\",\"maxTimeout\": 60000}'"
#curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + sys.argv[1] + "\",\"maxTimeout\": 60000, \"proxy\": { \"url\": \"http://127.0.0.1:1087\" }}'"
result = subprocess.check_output(curl_cmd, shell=True)



# 解析 JSON 数据
data = json.loads(result.decode('utf-8'))
response = data.get("solution", {}).get("response")
print(response)  # 输出 response 数据


# 使用正则表达式从结果中提取图片地址
pattern = r'https://img\.supjav\.com/images/.+?\.(jpg|png|bmp)'
try:
    matches = re.finditer(pattern, result.decode('utf-8'))
    found_images = False

    for match in matches:
        img_url = match.group()
        # 构建第二个 curl 命令来下载图片
        img_filename = img_url.split('/')[-1]
    
        # 检查目标文件是否存在
        if os.path.isfile(f"./src/{img_filename}"):
            print(f"文件 {img_filename} 已存在，跳过下载。")
            continue  # 跳过当前循环并继续下一个循环

        #curl_cmd_2 = f"curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{{\"cmd\": \"request.get\",\"url\":\"{img_url}\",\"maxTimeout\": 60000, \"proxy\": {{ \"url\": \"http://127.0.0.1:1085\" }} }}'"
        curl_cmd_2 = f"curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{{\"cmd\": \"request.get\",\"url\":\"{img_url}\",\"maxTimeout\": 60000 }}'"
       
        img_result = subprocess.run(curl_cmd_2, shell=True)
        img_data = json.loads(img_result.decode('utf-8'))
        img_response = img_data.get("solution", {}).get("response")
        with open(f"./src/{img_filename}", "wb") as file:
            file.write(img_response)
        os.system("pkill chrome; pkill chromedriver")
        found_images = True

    if not found_images:
        print("未找到图片链接。")
        os.system("pkill chrome; pkill chromedriver")

except TypeError:
    print("发生 TypeError，跳过错误并继续。")


os.system("pkill chrome; pkill chromedriver")
"""
