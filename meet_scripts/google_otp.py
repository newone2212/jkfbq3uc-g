import logging
import sys
import traceback
from time import sleep
import json
# fire below command for installing recording package
# sudo apt-get install pulseaudio-utils lame mpg123
# To install dependencies for pyvirtualdisplay required for headless fire below command:-
# sudo apt-get install xvfb xserver-xephyr tigervnc-standalone-server xfonts-base
from pyvirtualdisplay import Display

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from helper_functions import *

logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

try:
    with open('./meet_scripts/google_meet_properties.json', 'r') as f:
        properties = json.load(f)
except:
    logging.error('failed to open google_meet_properties.json')
    sys.exit(1)


def google_sign_in(driver: webdriver.Chrome) -> None:
    '''
    signs into google account
    '''
    driver.get(properties["url"]["google_sign_in_url"]) # open google sign in page
    logging.debug(f'{properties["url"]["google_sign_in_url"]} opened')
    sleep(2)
    email_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_text"]) # email text field
    email_text.send_keys(properties["login"]["email_id"])
    logging.debug(f'entered emailID: {properties["login"]["email_id"]}')
    email_next_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_next"])
    driver.execute_script("arguments[0].click();", email_next_btn) # next btn
    logging.debug('Clicked next btn')
    sleep(2)
    password_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_text"]) #pass text
    password_text.send_keys(properties["login"]["password"])
    logging.debug('Entered password')
    password_next_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_next"])
    driver.execute_script("arguments[0].click();", password_next_btn) # next btn


def main():

    display = Display(visible=False, size=(1366, 768))
    display.start()

    opt = get_chrome_options(True)
    opt.add_argument("--lang=en-GB")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opt)
    logging.debug('Driver started')

    try:

        google_sign_in(driver)
        sleep(2)

        # mobile_number = input('Enter phone number: ')
        
        # wait_and_find_element_by_xpath(driver, "//input[@type='tel']").send_keys(f'+91{mobile_number}')
        mobile_elem = wait_and_find_element_by_xpath(driver, "//input[@type='tel']")
        if mobile_elem:
            mobile_number = input('Enter phone number: ')
            mobile_elem.send_keys(f'+91{mobile_number}')
            wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphonecollectNext"]/div/button/span').click()

            otp = input('Enter 6-digit OTP: ')
            wait_and_find_element_by_xpath(driver, "//input[@type='tel']").send_keys(otp)
            wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphoneverifyNext"]/div/button/span', 1).click()
        print('Account verified, exiting...')
        

        driver.quit()
        display.stop()
        sys.exit(0)

    except Exception as e:
        traceback.print_exc()
        driver.quit()
        display.stop()
        sys.exit(1)
    

if __name__ == "__main__":
    main()
