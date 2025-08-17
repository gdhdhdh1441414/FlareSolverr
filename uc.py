#安装:pip3.8 install undetected-chromedriver
#wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
#yum install -y google-chrome-stable_current_x86_64.rpm


from pyvirtualdisplay import Display
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import os
import sys
import requests
import urllib.request
import re
import subprocess

print("运行前先杀死chrome")
os.system("pkill -9 chrome")
os.system('killall chrome')


url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
response = requests.get(url).text


m = re.match(r'.+?"url\"\:\"(https\:\/\/[\s\S]{2,85}chromedriver-linux64.zip).*', response)
zip_url  = m.group(1)
print ("Chrome下载地址:" + zip_url)


os.system(f"curl -o chromedriver-linux64.zip {zip_url}")

print("解压文件")
os.system("unzip -o chromedriver-linux64.zip -d /opt/")


chromedriver_version = subprocess.check_output("/opt/chromedriver-linux64/chromedriver --version", shell=True, text=True)
print("chromedriver版本:" + chromedriver_version)



if requests.get(sys.argv[1]).status_code == 200:
    page = requests.get(sys.argv[1])
    pageSource = page.content.decode('utf-8')
    print(pageSource)
else:
    display = Display(visible=0, size=(800, 600))
    display.start()

    class Demo:
        def set_chrome_option(self):
            self.chrome_options = uc.ChromeOptions()
            # chrome_options.headless = True
            # self.chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36')
            self.chrome_options.add_experimental_option('prefs', {'profile.default_content_setting_values': {'notifications': 2}})
            self.chrome_options.add_argument('disable-infobars')
            #self.chrome_options.add_argument('--proxy-server=http://127.0.0.1:1087')
            self.chrome_options.add_argument("--window-size=1920,1080")
            # self.chrome_options.add_argument('--headless')
            # user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
            self.chrome_options.add_argument('--disable-gpu')
            self.chrome_options.add_argument('--no-sandbox')
            self.chrome_options.add_argument('--disable-dev-shm-usage')
            self.chrome_options.add_argument('blink-settings=imagesEnabled=false')
            self.chrome_options.binary_location = "/usr/bin/google-chrome"        
        def run_all(self):
            try:
                self.set_chrome_option()
                
                browser = uc.Chrome(options=self.chrome_options, driver_executable_path= '/opt/chromedriver-linux64/chromedriver')
                browser.get(sys.argv[1])  #网站
                browser.implicitly_wait(200)
                pageSource = browser.page_source
                print(pageSource)
            finally:
                browser.quit()

        def main(self):
            self.run_all()

    if __name__ == "__main__":
        demo = Demo()
        demo.main()
    exit()
    display.stop()
os.system('pkill -9 python')
