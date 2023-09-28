import json
from random import choice
from time import sleep, time
from selenium import webdriver
from argparse import Namespace
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from taser import LOG
from taser.utils import file_collision_check
from taser.resources.user_agents import USER_AGENTS


def web_browser(url, load_time=0.05, screenshot=False, proxy=False, install=False):
    '''
    Make HTTP Requests with Selenium & Chome webdriver. returns similar
    object as requests for parsing

    Function Args:
        load_time (0.05) - Sleep timeout to allow page to load
        screenshot (False) - Filename to send HTTP screenshot
        proxy (False) - HTTP proxy web request
        install (False) - Auto install chromedriver. Warning does impact speed.

    Manually Install Chrome Driver:
        1) get chromedriver - http://chromedriver.chromium.org/downloads
        2) Make sure chromedriver matches version of chrome running
        3) Add to PATH (MacOS: /usr/local/bin)
    '''

    options = Options()
    options.add_argument("--headless")
    options.add_argument('log-level=3')
    options.add_argument("--disable-extensions")
    options.add_argument('ignore-certificate-errors')
    options.add_argument("user-agent={}".format(choice(USER_AGENTS)))
    options.set_capability("goog:loggingPrefs", {'performance': 'ALL'})
    options.add_argument(f'--proxy-server={proxy}') if proxy else False

    if install:
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        driver = webdriver.Chrome(options=options)

    try:
        start_time = time()
        driver.get(url)
        sleep(load_time)
        end_time = time()

        resp = Namespace(
            status_code=0,
            screenshot=False,
            title=driver.title,
            url=driver.current_url,
            time=(end_time - start_time),
            cookies=driver.get_cookies(),
            content=driver.page_source.encode("utf-8")
        )

        # Get status code from logs
        for log in driver.get_log('performance'):
            try:
                entry = json.loads(log['message'])
                url = entry['message']['params']['response']['url']
                code = entry['message']['params']['response']['status']
                if url == resp.url:
                    resp.status_code = code
            except:
                pass

        # Save screenshot
        if screenshot:
            fname = file_collision_check(screenshot, ext='png')
            driver.save_screenshot(fname)
            resp.screenshot = fname
        return resp
    except Exception as e:
        LOG.debug('Web_Browser:Error::{}'.format(e))
    finally:
        driver.quit()
    return False
