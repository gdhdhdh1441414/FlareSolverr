# -*- coding: UTF-8 -*- 
import time
import re
import os
import sys
import json
import subprocess
import html as html_lib
from datetime import datetime, timedelta, timezone

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
            generate_read_html()
            sys.exit(1)
        return None

    fail_count = 0  # 成功一次就清零
    return result
# ↑↑↑ 新增结束 ↑↑↑

# ↓↓↓ 新增：北京时间工具 & sharemania_read.html 生成 ↓↓↓
BEIJING_TZ = timezone(timedelta(hours=8))
BEIJING_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_beijing_now():
    return datetime.now(BEIJING_TZ)

def get_beijing_now_str():
    return get_beijing_now().strftime(BEIJING_TIME_FORMAT)

XML_PATH = './sharemania.xml'
READ_HTML_PATH = './sharemania_read.html'

def parse_rss_items(xml_content):
    """从最终的 sharemania.xml 内容中解析出每一条 item"""
    items = []
    for item_match in re.finditer(r'<item>([\s\S]*?)</item>', xml_content):
        item_xml = item_match.group(1)

        def extract(tag):
            m = re.search(rf'<{tag}><!\[CDATA\[([\s\S]*?)\]\]></{tag}>', item_xml)
            if m:
                return m.group(1)
            # 兼容没有用 CDATA 包裹的字段（比如报错条目的 title/link/author）
            m2 = re.search(rf'<{tag}>([\s\S]*?)</{tag}>', item_xml)
            return m2.group(1) if m2 else ''

        items.append({
            'title': extract('title'),
            'link': extract('link'),
            'description': extract('description'),
            'author': extract('author'),
            'pubDate': extract('pubDate'),
        })
    return items

def generate_read_html(xml_path=XML_PATH, html_path=READ_HTML_PATH):
    """把 sharemania.xml 转换成人类可读的 sharemania_read.html：
       标题 + 发布者/发布时间（北京时间）+ 默认折叠的全文描述（带明显的展开按钮）"""
    if not os.path.exists(xml_path):
        print(f"{xml_path} 不存在，跳过生成 {html_path}")
        return

    with open(xml_path, 'r', encoding='utf-8') as f:
        xml_content = f.read()

    items = parse_rss_items(xml_content)

    rows = []
    for it in items:
        title_esc = html_lib.escape(it['title']) if it['title'] else '（无标题）'
        author_esc = html_lib.escape(it['author']) if it['author'] else '未知'
        pubdate_esc = html_lib.escape(it['pubDate']) if it['pubDate'] else '未知'
        link_esc = html_lib.escape(it['link']) if it['link'] else '#'
        # description 本身是原网页富文本片段，直接原样放进折叠区域展示
        desc = it['description']

        rows.append(f'''
        <div class="item">
            <div class="item-title"><a href="{link_esc}" target="_blank" rel="noopener noreferrer">{title_esc}</a></div>
            <div class="item-meta">发布者：{author_esc} &nbsp;|&nbsp; 发布时间（北京时间）：{pubdate_esc}</div>
            <details class="item-desc">
                <summary class="toggle-btn">展开 / 收起 全文</summary>
                <div class="desc-content">{desc}</div>
            </details>
        </div>''')

    page = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ShareMania 更新列表</title>
<style>
    body {{ font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; background:#f5f5f5; margin:0; padding:20px; color:#222; }}
    h1 {{ font-size:20px; margin-bottom:16px; }}
    .item {{ background:#fff; border:1px solid #e0e0e0; border-radius:8px; padding:14px 16px; margin-bottom:12px; box-shadow:0 1px 2px rgba(0,0,0,0.04); }}
    .item-title a {{ font-size:16px; font-weight:600; color:#1a5fb4; text-decoration:none; }}
    .item-title a:hover {{ text-decoration:underline; }}
    .item-meta {{ font-size:13px; color:#666; margin:6px 0 8px; }}
    summary.toggle-btn {{
        display:inline-block; cursor:pointer; user-select:none;
        background:#1a5fb4; color:#fff; padding:4px 12px; border-radius:14px;
        font-size:13px; list-style:none;
    }}
    summary.toggle-btn::-webkit-details-marker {{ display:none; }}
    summary.toggle-btn:hover {{ background:#154a8f; }}
    .desc-content {{ margin-top:10px; padding-top:10px; border-top:1px dashed #ddd; line-height:1.6; font-size:14px; word-break:break-word; }}
    .desc-content img {{ max-width:100%; height:auto; }}
    .empty {{ color:#999; text-align:center; margin-top:40px; }}
</style>
</head>
<body>
<h1>ShareMania 更新列表（共 {len(items)} 条，生成时间：{get_beijing_now_str()} 北京时间）</h1>
{"".join(rows) if rows else '<div class="empty">暂无内容</div>'}
</body>
</html>'''

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(page)
    print(f"已生成人类可读页面：{html_path}")
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
    rss = f'{header}\n\t<item>\n\t\t<title>抓取首页出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t<pubDate><![CDATA[{get_beijing_now_str()}]]></pubDate>\n\t</item>\n{footer}'
    print(rss)
    with open('./sharemania.xml', 'w', encoding='utf-8') as f:
        f.write(rss)
    generate_read_html()
    sys.exit(0)

# ↓↓↓ 修改：不再用 links.txt，改成直接读现有 sharemania.xml 里已收录的 link 来判断"新链接" ↓↓↓
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
    # ↓↓↓ 新增：每次写入 xml 后，同步刷新人类可读页面 ↓↓↓
    generate_read_html()
    # ↑↑↑ 新增结束 ↑↑↑

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

# ↓↓↓ 新增：sharemania_error.log 相关 —— 记录/清理"重试3次仍失败"的链接 ↓↓↓
ERROR_LOG_PATH = './sharemania_error.log'

def load_error_log():
    """返回 {url: 首次失败时间字符串}"""
    entries = {}
    if os.path.exists(ERROR_LOG_PATH):
        with open(ERROR_LOG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) != 2:
                    continue
                u, t = parts
                entries[u] = t
    return entries

def save_error_log(entries):
    with open(ERROR_LOG_PATH, 'w', encoding='utf-8') as f:
        for u, t in entries.items():
            f.write(f"{u}\t{t}\n")

error_entries = load_error_log()
pending_24h_error_items = ""

for err_url in list(error_entries.keys()):
    err_relpath = re.sub(r'^https?://sharemania\.us/', '', err_url)
    if not err_relpath.endswith('/'):
        err_relpath += '/'

    if err_relpath in existing_links_relpath:
        # 已经成功抓取并写入xml，从错误日志移除
        print(f"错误日志中的链接已成功写入xml，移除记录：{err_url}")
        del error_entries[err_url]
        continue

    first_time = datetime.strptime(error_entries[err_url], BEIJING_TIME_FORMAT).replace(tzinfo=BEIJING_TZ)
    if get_beijing_now() - first_time >= timedelta(hours=24):
        print(f"链接连续24小时未成功抓取，追加提示到xml：{err_url}")
        pending_24h_error_items += f'\n\t<item>\n\t\t<title>{err_url} 过去24小时没有成功抓取，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{err_url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t<pubDate><![CDATA[{get_beijing_now_str()}]]></pubDate>\n\t</item>\n'
        del error_entries[err_url]

if pending_24h_error_items:
    write_rss(pending_24h_error_items)

save_error_log(error_entries)
# ↑↑↑ 新增结束 ↑↑↑

pattern = r'href\=\"(threads\/.+?)\"\>'
links = re.findall(pattern, response)

# ↓↓↓ 修改：新链接 = 首页抓到的链接 - xml 里已收录的链接（不再依赖 links.txt）↓↓↓
new_links = set(links) - existing_links_relpath
# ↑↑↑ 修改结束 ↑↑↑
if not new_links:  # or len(new_links) == 0
    print("无新链接")
    # ↓↓↓ 新增：即使没有新链接，也刷新一下可读页面（保证首次运行/xml 单独更新时页面存在）↓↓↓
    generate_read_html()
    # ↑↑↑ 新增结束 ↑↑↑
    sys.exit(0)  # 0 表示成功退出，GitHub Actions 不会报错

html_string = ""

# ↓↓↓ 新增：首页检测结果决定后续全部用哪个方案 ↓↓↓
use_uc = not response or "lastThreadTitle" not in response
# ↑↑↑ 新增结束 ↑↑↑

for link in new_links:
    # ↓↓↓ 修改：单条链接最多重试 3 次，3 次都失败就放弃这一条并记入错误日志，继续抓下一条，不再无限重试/退出脚本 ↓↓↓
    retry_count = 0
    max_retries = 3
    link_success = False

    while retry_count < max_retries:
        try:
            url = "https://sharemania.us/" + link
            print(url)
            os.system("pkill chrome;pkill chromedriver")

            if use_uc:
                uc_result = subprocess.run(
                    ["python", "uc.py", url],
                    capture_output=True,
                    text=True
                )
                response = uc_result.stdout
            else:
                payload_path = build_payload_file(url, 60000)
                curl_cmd = f"curl -s 'http://localhost:8191/v1' -H 'Content-Type: application/json' --data-binary @{payload_path}"
                result = run_flaresolverr_request(curl_cmd)
                if result is None:
                    retry_count += 1
                    print(f"该链接第 {retry_count} 次尝试失败：{url}")
                    continue

                data = json.loads(result.decode('utf-8'))
                response = data.get("solution", {}).get("response")
                print(result)

            if response is None:
                raise ValueError("Response is None")

            html_string += response
            link_success = True
            break

        except Exception as e:
            retry_count += 1
            print(f"该链接第 {retry_count} 次尝试出错: {str(e)}，url={url}")
            continue

    if not link_success:
        print(f"该链接连续 {max_retries} 次抓取全文失败，放弃，跳过：{url}")
        # ↓↓↓ 新增：记录到错误日志，若已存在则保留最早的发生时间不覆盖 ↓↓↓
        if url not in error_entries:
            error_entries[url] = get_beijing_now().strftime(BEIJING_TIME_FORMAT)
            print(f"已记录到 {ERROR_LOG_PATH}（首次失败时间）：{url}")
        else:
            print(f"该链接已在错误日志中，保留首次失败时间：{url}")
        save_error_log(error_entries)
        # ↑↑↑ 新增结束 ↑↑↑
    # ↑↑↑ 修改结束 ↑↑↑

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
        # ↓↓↓ 新增：author 可能被 <span class="styleN">...</span> 包裹，去掉标签只留纯文本用户名 ↓↓↓
        author = re.sub(r'\<[^\>]+\>', '', author).strip()
        # ↑↑↑ 新增结束 ↑↑↑
        article = re.sub(r'meta name\=\"description\"[\s\S]*?(\<article\>[\s\S]*?\<\/article\>)', r'\1', articles[i])

        if not author or len(author) > 30 or len(author) < 1:
            print("抓取全文出错，强制退出")
            generate_read_html()
            sys.exit(0)

        # ↓↓↓ 新增：每条新抓取的 item 记录北京时间发布时间，供 sharemania_read.html 展示 ↓↓↓
        pub_date_str = get_beijing_now_str()
        # ↑↑↑ 新增结束 ↑↑↑

        rss += f'''
                <item>
                <title><![CDATA[【{prefix}】{title}]]></title>
                <link><![CDATA[{link}]]></link>
                <description><![CDATA[{article}]]></description>
                <author><![CDATA[{author}]]></author>
                <pubDate><![CDATA[{pub_date_str}]]></pubDate>
                </item>

                '''

    write_rss(rss)
else:
    url = "https://sharemania.us/"
    error_item = f'\n\t<item>\n\t\t<title>出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t<pubDate><![CDATA[{get_beijing_now_str()}]]></pubDate>\n\t</item>\n'
    write_rss(error_item)
