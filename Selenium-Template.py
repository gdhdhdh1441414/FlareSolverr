# -*- coding: UTF-8 -*- 
import time
import re
import os
import sys
import json
import subprocess
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

# ↓↓↓ 新增：只保留最新50条 <item> ↓↓↓
def trim_items(xml_content, max_items=50):
    """只保留最新的 max_items 条 <item>...</item>，多余的丢弃"""
    items = re.findall(r'<item>[\s\S]*?</item>', xml_content)
    if len(items) <= max_items:
        return xml_content
    kept = items[:max_items]  # 新条目在前，所以前 max_items 个就是最新的
    body_only = re.sub(r'<item>[\s\S]*?</item>\s*', '', xml_content)
    idx = body_only.index(header) + len(header)
    new_content = body_only[:idx] + '\n'.join(kept) + body_only[idx:]
    return new_content
# ↑↑↑ 新增结束 ↑↑↑

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

    # ↓↓↓ 新增：写入前裁剪，只保留最新50条 ↓↓↓
    new_content = trim_items(new_content, max_items=50)
    # ↑↑↑ 新增结束 ↑↑↑

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

# ↓↓↓ 新增：sharemania_error.log 相关 —— 记录/清理"重试3次仍失败"的链接 ↓↓↓
ERROR_LOG_PATH = './sharemania_error.log'
BEIJING_TZ = timezone(timedelta(hours=8))
BEIJING_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_beijing_now():
    return datetime.now(BEIJING_TZ)

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
        pending_24h_error_items += f'\n\t<item>\n\t\t<title>{err_url} 过去24小时没有成功抓取，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{err_url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t</item>\n'
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
            sys.exit(0)
            
        rss += f'''
                <item>
                <title><![CDATA[【{prefix}】{title}]]></title>
                <link><![CDATA[{link}]]></link>
                <description><![CDATA[{article}]]></description>
                <author><![CDATA[{author}]]></author>
                </item>

                '''

    write_rss(rss)
else:
    url = "https://sharemania.us/"
    error_item = f'\n\t<item>\n\t\t<title>出错，请检查github：https://github.com/gdhdhdh1441414 {date}-{hour}</title>\n\t\t<link>{url}#{date}-{hour}</link>\n\t<author>sharemania</author>\n\t<description>sharemania</description>\n\t</item>\n'
    write_rss(error_item)
