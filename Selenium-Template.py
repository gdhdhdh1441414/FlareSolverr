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

# ↓↓↓ 新增：解析 cookie 字符串为 FlareSolverr 需要的 [{"name":..,"value":..}, ...] 格式 ↓↓↓
COOKIE_STRING = "lsc_active=1; lsc_active=1; lsc_active=1; xf_user=2354%2C5a2f477b349cd8bead; _lscache_vary=1; xf_keywords_2354=50%20Cent%20featuring%20Olivia%20-%20Candy%20Shop; xf_session=5ad56ae8; cf_clearance=R"

def parse_cookie_string(cookie_str):
    cookies = []
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if not pair:
            continue
        name, _, value = pair.partition('=')
        cookies.append({"name": name, "value": value})
    return cookies

COOKIES = parse_cookie_string(COOKIE_STRING)

def build_payload_file(url, max_timeout, payload_path="./flaresolverr_payload.json"):
    """把请求体写入临时 json 文件，避免在 shell 命令行里手动转义特殊字符"""
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": max_timeout,
        "cookies": COOKIES
    }
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return payload_path
# ↑↑↑ 新增结束 ↑↑↑

# ↓↓↓ 新增：FlareSolverr 连续失败计数器 ↓↓↓
fail_count = 0

def run_flaresolverr_request(curl_cmd):
    """执行 curl 请求，若报错或返回内容不含 'ShareMania.US</title>' 视为失败；
       连续失败2次则退出脚本。成功则重置计数并返回 result（bytes）。"""
    global fail_count
    try:
        result = subprocess.check_output(curl_cmd, shell=True)
        text = result.decode('utf-8', errors='ignore')
        if "ShareMania.US</title>" not in text:
            raise ValueError("返回内容不含 ShareMania.US</title>")
    except Exception as e:
        fail_count += 1
        print(f"FlareSolverr 请求失败（{e}），连续失败 {fail_count} 次")
        if fail_count >= 2:
            print("FlareSolverr 连续2次请求失败，脚本彻底退出")
            sys.exit(1)
        return None

    fail_count = 0  # 成功一次就清零
    return result
# ↑↑↑ 新增结束 ↑↑↑

# 使用 subprocess 模块调用 curl 命令，并捕获命令输出结果
# ↓↓↓ 修改：改用带 cookie 的 payload 文件发起请求 ↓↓↓
payload_path = build_payload_file("https://sharemania.us/", 16000)
curl_cmd = f"curl 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data-binary @{payload_path} | tee ./FlareSolverr.log"
result = run_flaresolverr_request(curl_cmd)
# ↑↑↑ 修改结束 ↑↑↑

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
        print("STDOUT:", uc_result.stdout[:200] if uc_result.stdout else "空")
        print("STDERR:", uc_result.stderr[:200] if uc_result.stderr else "空")
        print("returncode:", uc_result.returncode)
        
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

# ↓↓↓ 修改：不再用 links.txt，改成直接读现有 sharemania.xml 里已收录的 link 来判断"新链接" ↓↓↓
XML_PATH = './sharemania.xml'

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

def write_rss(new_items_str):
    """把新抓到的 item 合并进已有的 sharemania.xml（新条目插在最前面，老条目保留）；
       如果 xml 还不存在，就新建一个。"""
    if os.path.exists(XML_PATH):
        with open(XML_PATH, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        if header in existing_content:
            idx = existing_content.index(header) + len(header)
            new_content = existing_content[:idx] + new_items_str + existing_content[idx:]
        else:
            new_content = header + new_items_str + footer
    else:
        new_content = header + new_items_str + footer

    print(new_content)
    with open(XML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)

existing_links_relpath = set()
if os.path.exists(XML_PATH):
    with open(XML_PATH, 'r', encoding='utf-8') as f:
        existing_xml_content = f.read()
    for m in re.findall(r'<link><!\[CDATA\[(.+?)\]\]></link>', existing_xml_content):
        path = re.sub(r'^https?://sharemania\.us/', '', m)
        if not path.endswith('/'):
            path += '/'
        existing_links_relpath.add(path)
# ↑↑↑ 修改结束 ↑↑↑

pattern = r'href\=\"(threads\/.+?)\"\>'
links = re.findall(pattern, response)

# ↓↓↓ 修改：新链接 = 首页抓到的链接 - xml 里已收录的链接（不再依赖 links.txt）↓↓↓
new_links = set(links) - existing_links_relpath
# ↑↑↑ 修改结束 ↑↑↑
if not new_links:  # or len(new_links) == 0
    print("无新链接") 
    sys.exit(0)  # 0 表示成功退出，GitHub Actions 不会报错

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
                # ↓↓↓ 修改：改用带 cookie 的 payload 文件发起请求 ↓↓↓
                payload_path = build_payload_file(url, 60000)
                curl_cmd = f"curl -s 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data-binary @{payload_path}"
                result = run_flaresolverr_request(curl_cmd)
                if result is None:
                    # 本次失败但未达到连续2次，继续重试
                    continue
                # ↑↑↑ 修改结束 ↑↑↑

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

    # ↓↓↓ 修改：不再整份覆盖重写，改成把新 item 合并进已有 xml（老 item 保留）↓↓↓
    write_rss(rss)
    # ↑↑↑ 修改结束 ↑↑↑
else:
    # ↓↓↓ 修改：解析失败时也走合并逻辑，把错误提示插入已有 xml 最前面，而不是整份覆盖丢失历史 ↓↓↓
    url = "https://sharemania.us/"
    error_item = f'\n\t<item>\n\t\t<title>出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t</item>\n'
    write_rss(error_item)
    # ↑↑↑ 修改结束 ↑↑↑
