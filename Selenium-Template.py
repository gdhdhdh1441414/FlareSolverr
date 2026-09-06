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

# ↓↓↓ 新增：RSS 头尾、单条 item 的正则、以及"合并旧xml+新item，只保留最新50条"的工具函数 ↓↓↓
MAX_ITEMS = 50

header = '''<?xml version="1.0" encoding="utf-8"?>
<?xml-stylesheet type="text/xsl" href="rss1.xsl"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
 <title>sharemania</title>
 <link>http://www.sharemania.us/</link>
 <atom:link href="http://www.gettyimg.com/" rel="self" type="application/rss+xml" />

 '''

footer = '</channel></rss>'

ITEM_XML_RE = re.compile(r'<item>[\s\S]*?</item>')
ITEM_LINK_RE = re.compile(r'<link><!\[CDATA\[(.*?)\]\]></link>')

XML_PATH = './sharemania.xml'


def build_error_item(msg, err_url):
    """构造一条用于提示抓取出错的 item"""
    return (
        f'<item>\n\t<title><![CDATA[{msg} {date}-{hour}]]></title>\n'
        f'\t<link><![CDATA[{err_url}#{date}-{hour}]]></link>\n'
        f'\t<author><![CDATA[sharemania]]></author>\n'
        f'\t<description><![CDATA[sharemania]]></description>\n</item>'
    )


def load_old_items(xml_path=XML_PATH):
    """读取已有 xml 中的所有 <item>...</item> 块"""
    if not os.path.exists(xml_path):
        return []
    with open(xml_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return ITEM_XML_RE.findall(content)


def get_item_link(item_xml):
    m = ITEM_LINK_RE.search(item_xml)
    return m.group(1) if m else None


def save_merged_xml(new_item_blocks, xml_path=XML_PATH, max_items=MAX_ITEMS):
    """将本次新抓取到的 item 与旧 xml 中的 item 合并：
       - 新的排在前面，旧的排在后面
       - 若某条旧 item 的 link 与本次新抓取的重复，则丢弃旧的（保留新的）
       - 最终只保留最新 max_items 条，写回 xml_path
       返回最终写入的 xml 全文字符串"""
    old_items = load_old_items(xml_path)

    new_links_set = set(filter(None, (get_item_link(it) for it in new_item_blocks)))

    filtered_old_items = [it for it in old_items if get_item_link(it) not in new_links_set]

    combined = new_item_blocks + filtered_old_items
    combined = combined[:max_items]

    final_xml = header + "\n" + "\n".join(combined) + "\n" + footer
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(final_xml)
    return final_xml
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
    # ↓↓↓ 修改：不再整体覆盖xml，而是把出错提示合并进最新50条里，保留历史 item ↓↓↓
    home_url = "https://sharemania.us/"
    error_item = build_error_item("抓取首页出错，请检查github：https://github.com/gdhdhdh1441414", home_url)
    final_xml = save_merged_xml([error_item])
    print(final_xml)
    sys.exit(0)
    # ↑↑↑ 修改结束 ↑↑↑

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


regex_link = r'link rel\=\"canonical\" href="(.+?)\"'
regex_tit = r'\<title\>(.+?) \| ShareMania\.US'
regex_con = r'meta name\=\"description\"[\s\S]*?(\<article\>[\s\S]*?\<\/article\>)'
regex_prefix = r'Discussion in.+?\>(.+?)\<\/a\>'
regex_author = r'started by.+?\>(.+?)\<\/a\>'

html = html_string

if re.findall(regex_link, html) and re.findall(regex_tit, html):
    links = re.findall(regex_link, html)
    titles = re.findall(regex_tit, html)
    prefixs = re.findall(regex_prefix, html)
    authors = re.findall(regex_author, html)
    articles = re.findall(regex_con, html)

    # ↓↓↓ 修改：不再拼接成一个大字符串，而是收集成一个 item 列表，方便和旧 xml 合并 ↓↓↓
    new_item_blocks = []

    for i in range(len(links)):
        link = re.sub(r'link rel\=\"canonical\" href="(.+?)\"', r'\1', links[i])
        prefix = re.sub(r'\Discussion in.+?\>(.+?)\<\/a\>', r'\1', prefixs[i])
        title = re.sub(r'\<title\>(.+?) \| ShareMania\.US', r'\1', titles[i])
        author = re.sub(r'started by.+?\>(.+?)\<\/a\>', r'\1', authors[i])
        article = re.sub(r'meta name\=\"description\"[\s\S]*?(\<article\>[\s\S]*?\<\/article\>)', r'\1', articles[i])

        if not author or len(author) > 30 or len(author) < 1:
            print("抓取全文出错，强制退出")
            sys.exit(0)

        new_item_blocks.append(
            f'''<item>
                <title><![CDATA[【{prefix}】{title}]]></title>
                <link><![CDATA[{link}]]></link>
                <description><![CDATA[{article}]]></description>
                <author><![CDATA[{author}]]></author>
                </item>'''
        )
    # ↑↑↑ 修改结束 ↑↑↑

    # ↓↓↓ 修改：与旧 xml 合并，只保留最新 MAX_ITEMS 条，并写回文件 ↓↓↓
    final_xml = save_merged_xml(new_item_blocks)
    print(final_xml)
    # ↑↑↑ 修改结束 ↑↑↑

    # ↓↓↓ 修改：检查遗漏的逻辑改为——用最终写入 xml 的 link 和 new_links 对比，
    #         而不是用本次抓取到的原始 html 里解析出的 link 对比 ↓↓↓
    xml_links = set(ITEM_LINK_RE.findall(final_xml))

    def to_full_url(relative_link):
        full = "https://sharemania.us/" + relative_link
        return full if full.endswith('/') else full + '/'

    matched_new_links = set()
    for l in new_links:
        full_url = to_full_url(l)
        # 兼容 xml 中的 link 结尾是否带斜杠
        if full_url in xml_links or full_url.rstrip('/') in {x.rstrip('/') for x in xml_links}:
            matched_new_links.add(l)

    unmatched_new_links = new_links - matched_new_links
    if unmatched_new_links:
        with open('links.txt', 'r') as f:
            current_saved_links = set(f.read().splitlines())
        current_saved_links -= unmatched_new_links
        with open('links.txt', 'w') as f:
            for l in current_saved_links:
                f.write(l + '\n')
        print(f"以下链接本次未成功写入RSS，已从 links.txt 移除，下次将重新抓取：{unmatched_new_links}")
    # ↑↑↑ 修改结束 ↑↑↑
else:
    # ↓↓↓ 修改：解析彻底失败时，同样不整体覆盖xml，而是把出错提示合并进最新50条里 ↓↓↓
    err_home_url = "https://sharemania.us/"
    error_item = build_error_item("出错，请检查github：https://github.com/gdhdhdh1441414", err_home_url)
    final_xml = save_merged_xml([error_item])
    print(final_xml)
    # ↑↑↑ 修改结束 ↑↑↑

    # 本次全文解析彻底失败，new_links 全部视为未匹配，从 links.txt 移除以便下次重新抓取
    if new_links:
        with open('links.txt', 'r') as f:
            current_saved_links = set(f.read().splitlines())
        current_saved_links -= new_links
        with open('links.txt', 'w') as f:
            for l in current_saved_links:
                f.write(l + '\n')
        print(f"抓取全文解析出错，已将本次 new_links 从 links.txt 移除，下次将重新抓取：{new_links}")
