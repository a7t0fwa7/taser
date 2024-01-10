import socket
from os import path
from time import time
from random import choice
from seleniumwire import webdriver

from argparse import Namespace
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from taser import LOG
from taser.http import URLParser
from taser.utils import file_collision_check
from taser.resources.user_agents import USER_AGENTS


def web_browser(url, headers={}, cookies={}, timeout=3, screenshot=False, proxies=[], install=False):
    '''
    Make HTTP Requests with Selenium & Chrome webdriver. returns requests-like object for parsing

    Manually Install Chrome Driver:
        1) get chromedriver - http://chromedriver.chromium.org/downloads
        2) Make sure chromedriver matches version of chrome running
        3) Add to PATH (MacOS: /usr/local/bin)
    '''
    resp = False
    # Fix seleniumwire.thirdparty.mitmproxy.exceptions.TcpTimeout Error
    socket.setdefaulttimeout(timeout+5)

    options = Options()
    options.add_argument('--silent')
    options.add_argument('--headless')
    options.add_argument('--log-level=3')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-application-cache')
    options.add_argument('ignore-certificate-errors')

    wire_opts = {
        'verify_ssl': False,
        'proxy': get_proxy(proxies),
        'connection_timeout': timeout,
        'suppress_connection_errors': True,
    }

    if install:
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options, seleniumwire_options=wire_opts)
    else:
        driver = webdriver.Chrome(options=options, seleniumwire_options=wire_opts)

    # Add headers
    for header_name, header_value in headers.items():
        options.add_argument(f"--header={header_name}: {header_value}")

    # Randomize user-agent
    if 'User-Agent' not in headers.keys():
        options.add_argument("user-agent={}".format(choice(USER_AGENTS)))

    # Add cookies:
    for cookie_name, cookie_value in cookies.items():
        driver.add_cookie({'name': cookie_name, 'value': cookie_value})

    try:
        start_time = time()
        driver.get(url)
        driver.set_script_timeout(timeout)
        end_time = time()

        for request in driver.requests:
            if request.response and driver.current_url == request.url:
                resp = build_requests_object(request, driver, (end_time - start_time))
                resp.history = [build_requests_object(request) for request in driver.requests if 300 <= request.response.status_code < 400]

        # Save screenshot
        if screenshot:
            fname = file_collision_check(path.join(screenshot, URLParser.extract_subdomain(url)), ext='png')
            driver.save_screenshot(fname)
            resp.screenshot = fname

    except Exception as e:
        LOG.debug('Web_Browser:Error::{}'.format(e))
    finally:
        driver.quit()
    return resp


def get_proxy(proxies):
    # Randomize proxy input values and format for python-requests
    if not proxies:
        return {}
    tmp = choice(proxies)
    return {"http": tmp, "https": tmp}


def build_requests_object(request, driver=False, elapsed_time=False):
    return Namespace(
            history=[],
            driver=driver,
            request=request,
            url=request.url,
            screenshot=False,
            elapsed=elapsed_time,
            headers=request.response.headers,
            title=driver.title if driver else '',
            text=driver.page_source if driver else '',
            cookies=driver.get_cookies() if driver else {},
            content=driver.page_source.encode('utf-8') if driver else '',
            status_code=request.response.status_code if request.response.status_code else 0
    )
