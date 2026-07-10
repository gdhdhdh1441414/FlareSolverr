from seleniumbase import SB

with SB(uc=True, test=True, locale="en", xvfb=True) as sb:
    url = "https://sharemania.us/threads/evanescence-live-in-s%C3%A3o-paulo-2023-documentary-sanctuary-deluxe-bdrip-1080p.301716/"
    sb.activate_cdp_mode(url)
    sb.uc_gui_click_captcha()
    sb.sleep(2)
