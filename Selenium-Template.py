# -*- coding: UTF-8 -*- 
import time
import re
import os
import json
import subprocess
from datetime import datetime

subprocess.Popen(['sudo', 'python', 'src/flaresolverr.py'])

# 睡眠 20 秒以确保 flaresolverr.py 已经启动
time.sleep(32)

# 使用 subprocess 模块调用 curl 命令，并捕获命令输出结果
curl_cmd = "curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"https://sharemania.us/\",\"maxTimeout\": 60000}'"
result = subprocess.check_output(curl_cmd, shell=True)

# 解析 JSON 数据
data = json.loads(result.decode('utf-8'))
response = data.get("solution", {}).get("response")
#print(response)  # 输出 response 数据

pattern = r'href\=\"(threads\/.+?)\"\>'
links = re.findall(pattern, response)


with open('links.txt', 'r') as f:
    saved_links = set(f.read().splitlines())

# Find the new links
new_links = set(links) - saved_links


with open('links.txt', 'w') as f:
    for link in links:
        f.write(link + '\n')

        
html_string = ""

for link in new_links:
    url = "https://sharemania.us/" + link
    print(url)
    os.system("pkill chrome;pkill chromedriver")
    curl_cmd = "curl -s 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data '{\"cmd\": \"request.get\",\"url\":\"" + url + "\",\"maxTimeout\": 60000}'"
    result = subprocess.check_output(curl_cmd, shell=True)
    data = json.loads(result.decode('utf-8'))
    response = data.get("solution", {}).get("response")
    html_string += response

#print(html_string)

with open('./sharemania.html', 'w', encoding='utf-8') as f:
    f.write(html_string)


    
    

now = datetime.now()
date = now.strftime("%m-%d")
hour = now.strftime("%H")

regex_link = r'link rel\=\"canonical\" href="(.+?)\"'
regex_tit = r'\<title\>(.+?) \| ShareMania\.US'
regex_con = r'meta name\=\"description\" content=\"([\s\S]*?)\<div id\=\"loginBar\"'
regex_prefix = r'Discussion in.+?\>(.+?)\<\/a\>'
regex_author = r'started by.+?\>(.+?)\<\/a\>'

header = '''<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type="text/xsl" href="rss1.xsl"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
 <title>Getty</title>
 <link>http://www.gettyimg.com/</link>
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
        article = re.sub(r'meta name\=\"description\" content=\"([\s\S]*?)\<div id\=\"loginBar\"', '\1', articles[i], flags=re.DOTALL)
        


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
else:
    rss = f'{header}\n\t<item>\n\t\t<title>出错，请检查 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t</item>\n{footer}'
    print(rss)
    
with open('./sharemania.xml', 'w', encoding='utf-8') as f:
    f.write(rss_feed)
