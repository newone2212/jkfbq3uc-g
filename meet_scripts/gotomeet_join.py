import logging
import os
import signal
import subprocess
import sys
import traceback
from time import sleep
import json
import csv
import re
# fire below command for installing recording package
# sudo apt-get install pulseaudio-utils lame mpg123
# To install dependencies for pyvirtualdisplay required for headless fire below command:-
# sudo apt-get install xvfb xserver-xephyr tigervnc-standalone-server xfonts-base
from pyvirtualdisplay import Display

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from helper_functions import *


participant_list = list()

logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

try:
    with open('./meet_scripts/gotomeet_properties.json', 'r') as f:
        properties = json.load(f)
except:
    logging.error('failed to open google_meet_properties.json')
    sys.exit(1)

def join_meet(driver: webdriver.Chrome, audio_device: str) -> None:
    join_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["join_meet_btn"],4)
    if join_btn:
        join_btn.click()
        logging.debug("Clicked on 'Join my meeting'")    
    save_nd_ctn_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["save_and_continue_btn"],4)
    save_nd_ctn_btn.click()
    logging.debug('Clicked save and continue')
    save_nd_ctn_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["save_and_continue_btn"],4)
    save_nd_ctn_btn.click()
    logging.debug('Clicked save and continue')
    try:        
        wait_and_find_element_by_xpath(driver, properties["xpath"]["mic_btn"]).click()
        logging.debug('Switched off mic')
    except:
        logging.warning('Failed to mute mic')
    try:
        wait_and_find_element_by_xpath(driver, properties["xpath"]["cam_btn"]).click()
        logging.debug('Switched off camera')
    except:
        logging.warning('Failed to switch off camera')
    choose_audio_device(driver, audio_device)


def choose_audio_device(driver: webdriver.Chrome, audio_device: str) -> None:
    li = wait_and_find_element_by_xpath(driver, f"//*[contains(text(), '{audio_device}')]")
    driver.execute_script("arguments[0].click();", li)
    logging.info(f'Chose {audio_device} as audio device')


def wait_for_meet_to_start(driver: webdriver.Chrome, output: str, display: Display) -> None:
    if wait_and_find_element_by_xpath(driver, properties["xpath"]["ask_to_join_btn"]):
        sleep(120)
        driver.quit()
        remove_virtual_sink(output)
        display.stop()
        logging.info('Exiting as meet locked')
        sys.exit(1)
    while True:
        am_ready_btn = wait_and_find_element_by_xpath(driver, """//*[text()="Ok, I'm ready"]""",1)
        if am_ready_btn:
            am_ready_btn.click()
            logging.debug('Clicked ok, im ready')
            logging.info("Joined the meet")
            sleep(3)
            wait_and_find_element_by_xpath(driver, properties["xpath"]["name_input"],3).send_keys(properties["bot_name"])
            logging.debug("entered name")
            wait_and_find_element_by_xpath(driver, properties["xpath"]["submit_name_btn"],1).click()
            logging.debug('submitted name')
            return
        logging.debug('Bot waiting for meet to start')
        sleep(5)


def check_if_meet_active(driver: webdriver.Chrome, process: subprocess.Popen, output: str) -> None:
    global participant_list
    while True:
        if wait_and_find_element_by_xpath(driver, """//*[text()='The session has ended' or text()="You've been excused"]""",1):
            leave_process(driver, process, output)
            logging.debug('Exiting as meet has ended')
            return
        if wait_and_find_element_by_xpath(driver, properties["xpath"]["new_hardware_text"],1):
            wait_and_find_element_by_xpath(driver, properties["xpath"]["no_btn"]).click()
            logging.debug('clicked no on new hardware prompt')
        attendees = wait_and_find_elements_by_xpath(driver, properties["xpath"]["attendees"],1)
        if attendees:
            if len(attendees) == 1:
                leave_process(driver, process, output)
                logging.debug('Leaving as bot only one in meet')
                return
            elif len(attendees) > len(participant_list):
                temp_participant_list = []
                for attendee in attendees:
                    attendee_name = re.sub(r'\n.*', '', attendee.text)
                    if attendee_name != '[Waiting for name]':
                        temp_participant_list.append(attendee_name)
                if len(temp_participant_list) > len(participant_list):
                    participant_list = temp_participant_list
                    logging.debug('Updated attendee list')
        else:
            wait_and_find_element_by_xpath(driver, properties["xpath"]["show_ppl_btn"],1).click()
            logging.debug('Clicked participants tab')
        sleep(5)


def leave_process(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str) -> None:
    """
    function to kill driver and recording process
    """
    driver.quit()
    logging.debug('Driver closed')
    process.kill()
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)  
    logging.info(f'Recording process pid: {process.pid} kiled')
    remove_virtual_sink(sink_name)
    create_participants_csv(sink_name)


def create_participants_csv(output_name: str):
    """
    Stores the names of participants in a csv file with the same recording name.
    """
    global participant_list
    with open(f'./recordings/{output_name[:-4]}.csv', mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['name'])
        for name in participant_list:
            csv_writer.writerow([name])
    logging.info(f'Stored participant list in: {output_name[:-4]}.csv')


def main(url: str, output: str):

    start_pulseaudio()

    # start virtual display for headless
    display = Display(visible=False, size=(1366, 768))
    display.start()

    opt = get_chrome_options(True)
    opt.add_argument("--lang=en-GB")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opt)
    logging.debug('Driver started')

    try:

        create_virtual_sink(output)

        sleep(2)
        driver.get(url) # open meet url
        logging.debug(f'{url} opened')

        join_meet(driver, output)

        wait_for_meet_to_start(driver, output, display)

        process = record_meet(output)
        
        check_if_meet_active(driver, process, output)

        display.stop()

        logging.info('SUCCESS: Exiting script with ret code 0')
        sys.exit(0)

    except Exception as e:
        traceback.print_exc()
        try:            
            driver.quit()
            logging.debug('Killed driver')
            display.stop()
            try:
                process.kill()
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                logging.info(f'Recording process pid: {process.pid} kiled')
            finally:
                remove_virtual_sink(output)
        finally:            
            logging.error('FAILURE: Exiting script with ret code 1')
            sys.exit(1)


if __name__ == "__main__":
    args = parse_arguments()
    logging.info(f'Starting script with url={args.url} and output file={args.output_file}')
    main(args.url, args.output_file)
