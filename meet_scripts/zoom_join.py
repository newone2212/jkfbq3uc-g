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
from pyvirtualdisplay import Display, display

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from helper_functions import *


participant_list = list()

logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

try:
    with open('meet_scripts/zoom_properties.json', 'r') as f:
        properties = json.load(f)
except:
    logging.error('failed to open zoom_properties.json')
    sys.exit(1)


def join_meet(driver: webdriver.Chrome, audio_device: str, display: Display):
    """
    joins the meet
    """
    try:
        join_audio_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["join_audi_btn"])
        if join_audio_btn:
            join_audio_btn.click()
            logging.debug('enable the audio button')
    except:
        logging.warning('failed to enable audio button')
    try:
        mic_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["mic_btn"])
        if mic_btn:
            mic_btn.click()
            logging.debug('Muted the mic')
    except:
        logging.warning('failed to mute')
    try:
        cam_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["cam_btn"])
        if cam_btn:
            cam_btn.click()
            logging.debug('Switched off cam')
    except:
        logging.debug('Failed to switch off cam')
    username_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["username_text"],1)
    if username_text:
        username_text.send_keys(properties["bot_name"])
    join_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["join_btn"],1)
    if join_btn:
        join_btn.click()
    sleep(3)
    check_if_meet_invalid(driver, audio_device, display)
    meet_not_started_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["meet_not_started_text"],3)
    if meet_not_started_text:
        while True:
            sleep(5)
            meet_not_started_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["meet_not_started_text"],1)
            if not meet_not_started_text:
                check_if_meet_invalid(driver, audio_device, display)
                break
            logging.debug('Meeting not yet started')
    
    sleep(3)
    in_lobby_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["in_lobby_text"],5)
    if in_lobby_text:
        while True:
            sleep(5)            
            meet_end_text_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["meet_end_text"],2)
            if meet_end_text_btn:
                driver.quit()
                logging.debug('Driver killed')
                remove_virtual_sink(audio_device)
                display.stop()
                logging.info('Exiting as meet has ended/bot was denied entry')
                sys.exit(1)
            if wait_and_find_element_by_xpath(driver, properties["xpath"]["audioOptionMenu_btn"],1):
                break
            in_lobby_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["in_lobby_text"],1)
            if in_lobby_text:
                if in_lobby_text.text == 'Please wait, the meeting host will let you in soon.':
                    logging.debug('Waiting in lobby')
    logging.debug('Joined meet')
    choose_audio_device(driver, audio_device)
    disable_video(driver)


def disable_video(driver: webdriver.Chrome) -> None:
    try:
        disable_video_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["disable_video_btn"],1)
        driver.execute_script("arguments[0].click();", disable_video_btn)
        logging.debug('Disabled video receiving')
    except:
        logging.warning('Failed to disable video receiving')


def check_if_meet_invalid(driver: webdriver.Chrome, sink_name: str, display: Display):
    """
    Checks if meet link is invalid
    """
    meet_invalid = wait_and_find_element_by_xpath(driver, properties["xpath"]["meet_invalid_text"],2)
    if meet_invalid:
        if meet_invalid.text.startswith('This meeting link is invalid'):
            driver.quit()
            logging.debug('driver killed')
            remove_virtual_sink(sink_name)
            display.stop()
            logging.info('exiting because link invalid')
            sys.exit(1)


def choose_audio_device(driver: webdriver.Chrome, audio_device: str) -> None:
    """
    Selects the newly created audio device from the meet audio settings
    """
    audioOptionMenu_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["audioOptionMenu_btn"])
    if audioOptionMenu_btn:
        driver.execute_script("arguments[0].click();", audioOptionMenu_btn)
        wait_and_find_element_by_xpath(driver, f"//*[text()='{audio_device}']",1).click()
    logging.debug('Switched audio device')


def check_if_meet_active(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str) -> None:
    """
    checks if host has ended the meet and takes the recording process as arg to later kill it
    """
    global participant_list
    while True:
        meet_end_text_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["meet_end_text"],2)
        if meet_end_text_btn:
            leave_process(driver, process, sink_name)
            logging.info('Exiting as meet has ended')
            return
        attendees = wait_and_find_elements_by_xpath(driver, properties["xpath"]["attendees"],5)
        if attendees:
            if len(attendees) == 1:
                leave_end_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["leave_end_btn"])
                driver.execute_script("arguments[0].click();", leave_end_btn)
                leave_end_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["leave_end_final_btn"])
                driver.execute_script("arguments[0].click();", leave_end_btn)
                leave_process(driver, process, sink_name)
                logging.info('Leaving as bot is the only attendee')
                return
            elif len(attendees) > len(participant_list):
                participant_list = [re.sub(r'\s*computer audio.*', '', attendee.get_attribute('aria-label')) for attendee in attendees]
        else:
            participants_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["participants_btn"])
            if participants_btn:
                driver.execute_script("arguments[0].click();", participants_btn)
                continue        
        sleep(5)


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


def main(url: str, output: str):

    start_pulseaudio()

    # start virtual display for headless
    display = Display(visible=False, size=(1366, 768))
    display.start()

    opt = get_chrome_options(True)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opt)
    logging.debug('Driver started')

    try:

        create_virtual_sink(output)

        sleep(2)
        driver.get(url.replace('/j/', '/wc/join/')) # open meet url
        logging.debug(f'{url} opened')

        join_meet(driver, output, display)

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
            remove_virtual_sink(output)
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