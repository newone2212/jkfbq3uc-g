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
from tracking import SpeakerTracker
from datetime import datetime


participant_list = list()
recording_start_datetime = None  


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
    email_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_text"],5) # email text field
    email_text.send_keys(properties["login"]["email_id"])
    sleep(2)
    logging.debug(f'entered emailID: {properties["login"]["email_id"]}')
    email_next_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_next"],5) 
    driver.execute_script("arguments[0].click();", email_next_btn) # next btn
    logging.debug('Clicked next btn')
    sleep(2)
    password_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_text"],5) #pass text
    password_text.send_keys(properties["login"]["password"])
    logging.debug('Entered password')
    sleep(2)
    password_next_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_next"],5)
    driver.execute_script("arguments[0].click();", password_next_btn) # next btn
    logging.info('Signed in into google')
    sleep(2)
    mobile_elem = wait_and_find_element_by_xpath(driver, "//input[@type='tel']", timeout=3)
    if mobile_elem:
        mobile_number = input('Enter phone number: ')
        mobile_elem.send_keys(f'+91{mobile_number}')
        wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphonecollectNext"]/div/button/span').click()

        otp = input('Enter 6-digit OTP: ')
        otp_box = wait_and_find_element_by_xpath(driver, "//input[@type='tel']")
        if otp_box:
            otp_box.send_keys(otp)
        next_btn = wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphoneverifyNext"]/div/button/span', 1)
        if next_btn:
            next_btn.click()
    print('Account verified, exiting...')

def join_meet(driver: webdriver.Chrome, output: str) -> None:
    '''
    joins the meet
    '''    
    sleep(10)    
    try:
        # driver.execute_script('''document.querySelector('[aria-label="Turn off microphone (ctrl + d)"]').click();''')
        cam_off_butn = wait_and_find_element_by_xpath(driver, "//div[contains(@aria-label, 'Turn off camera (ctrl + e)')]",2)
        if cam_off_butn:
            cam_off_butn.click()
        logging.debug('Switched off mic')
    except:
        logging.warning('Failed to switch off mic')
    try:
        # driver.execute_script('''document.querySelector('[aria-label="Turn off camera (ctrl + e)"]').click();''')
        spkr_off_butn = wait_and_find_element_by_xpath(driver, "//div[contains(@aria-label, 'Turn off microphone (ctrl + d)')]",2)
        if spkr_off_butn:
            spkr_off_butn.click()
        logging.debug('Switched off camera')
    except:
        logging.warning('Failed to switch off camera')
   
    choose_audio_device(driver, output) # choose new audio device
    sleep(2)
    ask_to_join_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["ask_to_join_btn"],2)
    if ask_to_join_btn:
        driver.execute_script("arguments[0].click();", ask_to_join_btn) # Ask to join / Join now btn
    logging.debug('Clicked "Ask to join/Join now" btn')
    logging.info('Joined/sent request for joining')
    sleep(12)


def choose_audio_device(driver: webdriver.Chrome, audio_device: str) -> None:
    '''
    Selects the newly created audio device from the meet audio settings
    '''
    check_audio_video_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["check_audio_video_btn"],2)
    if check_audio_video_btn:
        check_audio_video_btn.click()
    logging.debug('Clicked "Check your audio and video" btn')
    sleep(2)
    audio_and_video_tab = wait_and_find_element_by_xpath(driver, properties["xpath"]["audio_and_video_tab"],2)
    if audio_and_video_tab:
        driver.execute_script("arguments[0].click();", audio_and_video_tab)
    logging.debug('Clicked Audio & video tab')
    sleep(2)
    speaker_dropdown = wait_and_find_element_by_xpath(driver, properties["xpath"]["speaker_dropdown"],2)
    if speaker_dropdown:
        speaker_dropdown.click()
    logging.debug('Clicked speaker dropdown')
    sleep(2)
    device = wait_and_find_element_by_xpath(driver, "//*[contains(text(),'" + audio_device + "')]",2)#.click() # select device
    if device:
        driver.execute_script("arguments[0].click();", device)
    logging.debug(f'Selected {audio_device} from dropdown')
    sleep(2)
    close_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["audio_and_video_tab_close"],2)
    if close_btn:
        driver.execute_script("arguments[0].click();", close_btn)
    logging.debug('Closed audio settings')
    logging.info(f'Chose {audio_device} as audio device')


def leave_process(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str, tracker: SpeakerTracker) -> None:    
    tracker.stop_tracking()
    global recording_start_datetime
    tracker.export_to_csv(f'./recordings/{sink_name[:-4]}_speaker_timestamps.csv', meeting_start_time=recording_start_datetime)
    # tracker.export_to_json(f'./recordings/{sink_name[:-4]}.json')

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
    logging.info(f'Checking participant list: {participant_list}')
    with open(f'./recordings/{output_name[:-4]}.csv', mode='w') as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(['name'])
        # csv_writer.writerow(['Acta Assistant'])
        for name in set(participant_list):
            csv_writer.writerow([name])
    logging.info(f'Stored participant list in: {output_name[:-4]}.csv')


def check_if_meet_active(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str, tracker: SpeakerTracker) -> None:    
    """
    leaves the meet if bot is the only participant or has been removed from the meet/meet has ended
    """
    global participant_list
    while True:
        sleep(1)
        show_people_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["show_people_btn"], 3)
        if show_people_btn:
            people = wait_and_find_elements_by_xpath(driver, properties["xpath"]["people_list"], 2)
            if people:
                if len(people) == 1:
                    logging.info('Preparing to leave the meet')
                    call_end_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["call_end_btn"])
                    driver.execute_script("arguments[0].click();", call_end_btn)
                    logging.debug('Clicked leave meet btn')
                    leave_process(driver, process, sink_name, tracker)
                    return
                elif len(people) > len(participant_list):
                    participant_list = [re.sub(r'\n.+', '', x.text).replace('keep_pin','') for x in people]
                    participant_list = [w for w in participant_list if w.strip() != '']
                    #logging.debug('Updated participant list')
            else:
                click_show_people(driver=driver, properties=properties)
        else:
            logging.info('Preparing to leave the meet')
            leave_process(driver, process, sink_name, tracker)
            return
        
def click_show_people(driver, properties):
    try:
        show_people_btn = driver.find_element_by_xpath(properties["xpath"]["show_people_btn"])
        if show_people_btn:
            try:
                driver.execute_script("arguments[0].click();", show_people_btn)
                logging.debug('Clicked show people button')
            except:
                logging.warning('Failed to click show people button')
    except:
        logging.warning('Failed to check show people button')


def wait_for_meet_to_start(driver: webdriver.Chrome, sink_name: str, display: Display):
    """
    starts recording after the bot has joined the meet and returns the process
    """
    global recording_start_datetime

    while True:
        show_people_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["show_people_btn"], 3)
        if show_people_btn:
            logging.info('Joined meet')  
            click_show_people(driver=driver, properties=properties)
            process = record_meet(sink_name)
            recording_start_datetime = datetime.now()  
            logging.debug(f"Recording starttime {recording_start_datetime}")
            tracker = SpeakerTracker(driver, properties, verbose=False)
            tracker.start_tracking()
            return process, tracker
        in_lobby_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["in_lobby_text"], 2)
        if in_lobby_text:
            logging.info('Waiting in the lobby')
            sleep(5)
            continue
        else:
            show_people_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["show_people_btn"], 2)
            if show_people_btn:
                logging.info('Joined meet')
                click_show_people(driver=driver, properties=properties)
                recording_start_datetime = datetime.now()  
                logging.debug(f"Recording starttime {recording_start_datetime}")
                process = record_meet(sink_name)
                tracker = SpeakerTracker(driver, properties, verbose=False)
                tracker.start_tracking()
                return process, tracker
            logging.info('Preparing to exit process as bot was denied entry')
            driver.quit()
            logging.debug('Driver closed')
            remove_virtual_sink(sink_name)
            display.stop()
            logging.info('FAILURE: Exiting script with ret code 1')
            sys.exit(1)


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
        google_sign_in(driver)

        sleep(2)
        driver.get(url) # open meet url
        logging.debug(f'{url} opened')

        join_meet(driver, output)
        sleep(2)

        process, tracker = wait_for_meet_to_start(driver, output, display)
        
        check_if_meet_active(driver, process, output, tracker)

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