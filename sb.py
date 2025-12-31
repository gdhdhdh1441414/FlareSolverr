from seleniumbase import SB
import time
import sys
from pyvirtualdisplay import Display

display = Display(visible=0, size=(1920, 1080))  
display.start()

# 设置代理（支持HTTP/HTTPS/SOCKS）
# proxy_string = "http://127.0.0.1:1080"  # 认证代理
# proxy_string = "http://host:port"  # 无需认证的代理
# proxy_string = "socks5://host:port"  # SOCKS5代理

# 定义自定义UA
custom_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 方法1：在SB初始化时直接设置UA（推荐）
with SB(uc=True, test=True, locale="en", agent=custom_ua) as sb:
    url = sys.argv[1]
    
    # 方法2：通过CDP模式修改UA（如果需要动态修改）
    # sb.activate_cdp_mode(url)
    # sb.execute_cdp_cmd(
    #     "Network.setUserAgentOverride",
    #     {
    #         "userAgent": custom_ua,
    #         "platform": "Windows",
    #         "acceptLanguage": "en-US,en;q=0.9"
    #     }
    # )
    
    sb.activate_cdp_mode(url)
    sb.sleep(2)
    sb.solve_captcha()
    sb.sleep(6)
    
    
    page_source = sb.get_page_source()
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    print(page_source)

display.stop() 
