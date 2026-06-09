# -*- coding: UTF-8 -*- 
import time
import re
import os
import sys
import json
import subprocess
from datetime import datetime

now = datetime.now()
date = now.strftime("%m-%d")
hour = now.strftime("%H")

#subprocess.Popen(['sudo', 'python', 'src/flaresolverr.py'])

# 睡眠 20 秒以确保 flaresolverr.py 已经启动
time.sleep(36)

# 使用 subprocess 模块调用 curl 命令，并捕获命令输出结果
curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"https://sharemania.us/\",\"maxTimeout\": 60000}' | tee ./FlareSolverr.log"

result = subprocess.check_output(curl_cmd, shell=True)

# 假设 result 是字节数据（如从网络请求获取的响应）
try:
    # 尝试解析 JSON
    data = json.loads(result.decode('utf-8'))
    response = data.get("solution", {}).get("response")
    # ↓↓↓ 新增：如果 response 有问题或不含 lastThreadTitle，改用 uc.py ↓↓↓
    if not response or "lastThreadTitle" not in response:
        uc_result = subprocess.run(
            ["python", "uc.py", "https://sharemania.us/"],
            capture_output=True,
            text=True
        )
        response = uc_result.stdout
    # ↑↑↑ 新增结束 ↑↑↑
    with open("sharemania...html", "w", encoding="utf-8") as file:
        file.write(f"{response}")
except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as e:
    # 如果解析失败（无效 JSON、非字节数据、解码错误等）
    print(f"解析 JSON 失败: {e}")
    # ↓↓↓ 新增：解析异常时也改用 uc.py ↓↓↓
    uc_result = subprocess.run(
        ["python", "uc.py", "https://sharemania.us/"],
        capture_output=True,
        text=True
    )
    response = uc_result.stdout
    # ↑↑↑ 新增结束 ↑↑↑
    with open("sharemania...html", "w", encoding="utf-8") as file:
        file.write(f"{response}")


if response is None:
    rss = f'{header}\n\t<item>\n\t\t<title>抓取首页出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t</item>\n{footer}'
    print(rss)
    with open('./sharemania.xml', 'w', encoding='utf-8') as f:
        f.write(rss)
    sys.exit(0)

pattern = r'href\=\"(threads\/.+?)\"\>'
links = re.findall(pattern, response)

with open('links.txt', 'r') as f:
    saved_links = set(f.read().splitlines())

# Find the new links
new_links = set(links) - saved_links
if not new_links:  # or len(new_links) == 0
    print("无新链接") 
    sys.exit(0)  # 0 表示成功退出，GitHub Actions 不会报错

if len(links) != 0 and len(links) >= 5:
    with open('links.txt', 'w') as f:
        for link in links:
            f.write(link + '\n')

html_string = ""

# ↓↓↓ 新增：首页检测结果决定后续全部用哪个方案 ↓↓↓
use_uc = not response or "lastThreadTitle" not in response
# ↑↑↑ 新增结束 ↑↑↑

for link in new_links:
    while True:
        try:
            url = "https://sharemania.us/" + link
            print(url)
            os.system("pkill chrome;pkill chromedriver")

            # ↓↓↓ 新增：根据标志选择方案 ↓↓↓
            if use_uc:
                uc_result = subprocess.run(
                    ["python", "uc.py", url],
                    capture_output=True,
                    text=True
                )
                response = uc_result.stdout
            else:
                curl_cmd = "curl -s 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + url + "\",\"maxTimeout\": 60000}'"
                result = subprocess.check_output(curl_cmd, shell=True)
                data = json.loads(result.decode('utf-8'))
                response = data.get("solution", {}).get("response")
                print(result)
            # ↑↑↑ 新增结束 ↑↑↑

            if response is None:
                raise ValueError("Response is None")

            html_string += response
            break

        except Exception as e:
            print("An error occurred:", str(e))
            continue

with open('./sharemania_all_page.html', 'w', encoding='utf-8') as f:
    f.write(html_string)


regex_link = r'link rel\=\"canonical\" href="(.+?)\"'
regex_tit = r'\<title\>(.+?) \| ShareMania\.US'
regex_con = r'meta name\=\"description\"[\s\S]*?(\<article\>[\s\S]*?\<\/article\>)'
regex_prefix = r'Discussion in.+?\>(.+?)\<\/a\>'
regex_author = r'started by.+?\>(.+?)\<\/a\>'

header = '''<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type="text/xsl" href="rss1.xsl"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
 <title>sharemania</title>
 <link>http://www.sharemania.us/</link>
 <atom:link href="http://www.gettyimg.com/" rel="self" type="application/rss+xml" />

 '''

footer = '</channel></rss>'

html = html_string

if re.findall(regex_link, html) and re.findall(regex_tit, html):
    links = re.findall(regex_link, html)
    titles = re.findall(regex_tit, html)
    prefixs = re.findall(regex_prefix, html)
    authors = re.findall(regex_author, html)
    articles = re.findall(regex_con, html)  
    
    rss = ""

    for i in range(len(links)):
        link = re.sub(r'link rel\=\"canonical\" href="(.+?)\"', r'\1', links[i])
        prefix = re.sub(r'\Discussion in.+?\>(.+?)\<\/a\>', r'\1', prefixs[i])
        title = re.sub(r'\<title\>(.+?) \| ShareMania\.US', r'\1', titles[i])
        author = re.sub(r'started by.+?\>(.+?)\<\/a\>', r'\1', authors[i])
        article = re.sub(r'meta name\=\"description\"[\s\S]*?(\<article\>[\s\S]*?\<\/article\>)', r'\1', articles[i])

        if not author or len(author) > 30 or len(author) < 1:
            print("抓取全文出错，强制退出")
            sys.exit(0)
            
        rss += f'''
                <item>
                <title><![CDATA[【{prefix}】{title}]]></title>
                <link><![CDATA[{link}]]></link>
                <description><![CDATA[{article}]]></description>
                <author><![CDATA[{author}]]></author>
                </item>

                '''

    rss_feed = header + rss + footer

    print(rss_feed)
    with open('./sharemania.xml', 'w', encoding='utf-8') as f:
        f.write(rss_feed)
else:
    url = "https://sharemania.us/"
    rss = f'{header}\n\t<item>\n\t\t<title>出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t</item>\n{footer}'
    print(rss)
    with open('./sharemania.xml', 'w', encoding='utf-8') as f:
        f.write(rss)
