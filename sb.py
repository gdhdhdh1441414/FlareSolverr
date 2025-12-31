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

with SB(uc=True, test=True, locale="en") as sb:
    url = sys.argv[1]
    sb.activate_cdp_mode(url)
    sb.sleep(2)
    sb.solve_captcha()
    sb.sleep(6)
    
    page_source = sb.get_page_source()
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    print(page_source)

display.stop()
