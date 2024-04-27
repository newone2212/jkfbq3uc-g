import os
import signal
import subprocess
import sys
import traceback
from time import sleep
import logging
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
    with open('meet_scripts/ms_teams_properties.json', 'r') as f:
        properties = json.load(f)
except:
    logging.error('failed to open ms_teams_properties.json')
    sys.exit(1)


def join_meet(driver: webdriver.Chrome, audio_device: str) -> None:
    """
    joins the meet
    """
    '''
    sign_in_ele = wait_and_find_element_by_xpath(driver, "//*[contains(text(),'Sign in')]")
    if sign_in_ele:
        email_id_text = wait_and_find_element_by_xpath(driver, '//*[@id="i0116"]')
        email_id_text.send_keys(EMAIL_ID)
        wait_and_find_element_by_xpath('//*[@id="idSIButton9"]').click()
        sleep(2)
        password_text = wait_and_find_element_by_xpath(driver, '//*[@id="i0118"]')
        password_text.send_keys(PASSWORD)
        wait_and_find_element_by_xpath(driver, '//*[@id="idSIButton9"]').click()
    '''
    join_on_web_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["join_on_web_btn"])
    if join_on_web_btn:
        driver.execute_script("arguments[0].click();", join_on_web_btn)
    logging.debug('Clicked on "Continue on this browser"')
    sleep(5)
    # driver.execute_script(f"document.getElementById('username').value='{properties['bot_name']}'")
    # above line doesnt work becoz this doesn't change some classes
    # username_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["username_text"])
    frame = wait_and_find_element_by_xpath(driver,"//iframe")
    if frame:
        driver.switch_to.frame(frame)
    username_text = wait_and_find_element_by_xpath(driver, "//input[@placeholder='Type your name']")
    if username_text:
        username_text.send_keys(properties['bot_name'])
    logging.debug(f"Set bot name: {properties['bot_name']}")    

    try:
        # driver.execute_script('''document.querySelector('[track-summary="Toggle camera OFF in meeting pre join screen"]').click()''')
        camera_inp = wait_and_find_element_by_xpath(driver,"//div[@title='Camera']")
        if camera_inp:    
            driver.execute_script("arguments[0].click();", camera_inp)
        logging.debug('Switched off cam')
    except:
        logging.warning('Failed to switch off cam')

    try:
        # driver.execute_script('''document.querySelector('[track-summary="Toggle microphone OFF in meeting pre join screen"]').click()''')
        mic_inp = wait_and_find_element_by_xpath(driver,"//div[@title='Microphone']")
        if mic_inp:    
            driver.execute_script("arguments[0].click();", mic_inp)
        logging.debug('Switched off mic')
    except:
        logging.warning('Failed to switch off mic')
    
    choose_audio_device(driver, audio_device)   # choose audio device from meet settings
    # join_now_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["join_now_btn"])
    join_btn = wait_and_find_element_by_xpath(driver, "//button[contains(@aria-label, 'Join now')]")
    if join_btn:
        driver.execute_script("arguments[0].click();", join_btn) # join meeting
    logging.debug('Clicked "Join now"')
    logging.info('Joined/sent request for joining')


def choose_audio_device(driver: webdriver.Chrome, audio_device: str) -> None:
    '''
    Selects the newly created audio device from the meet audio settings
    '''
    settings_btn = wait_and_find_element_by_xpath(driver,properties["xpath"]["settings_btn"])
    if settings_btn:
        driver.execute_script("arguments[0].click();", settings_btn)
    logging.debug('Clicked audio settings btn')
    speaker_btn = wait_and_find_element_by_xpath(driver,properties["xpath"]["speaker_btn"])
    if speaker_btn:
        driver.execute_script("arguments[0].click();", speaker_btn) # click speaker button
    logging.debug('Clicked speaker dropdown')
    device_btn = wait_and_find_element_by_xpath(driver, f"//li[@aria-label='{audio_device}']")
    if device_btn:
        driver.execute_script("arguments[0].click();", device_btn) # select device
    logging.debug(f'Selected {audio_device} from dropdown')
    logging.info(f'Chose {audio_device} as audio device')


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


def check_if_meet_active(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str) -> None:
    '''
    checks if host has ended the meet and takes the recording process as arg to later kill it
    '''
    global participant_list
    while True:
        sleep(5)
        roster_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["roster_btn"], 3)
        # roster btn to see list of attendees
        if roster_btn:
            driver.execute_script("arguments[0].click();", roster_btn)
            # attendees = wait_and_find_elements_by_xpath(driver, properties["xpath"]["attendees"], 5)
            # number_of_attendees = sum([int(x.text[1:-1]) for x in attendees if x.text != ''])
            num_participants = wait_and_find_element_by_xpath(driver, properties["xpath"]["participants"], 3)
            if num_participants:
                participants_text = re.search('\d+',num_participants.text)
                if participants_text:
                    number_of_attendees = int(participants_text[0])
                    # driver.execute_script("arguments[0].click();", roster_btn)
            # number of attendees + presenters after removing the brackets in received webelement text 
            if number_of_attendees == 1:
                logging.info('Preparing to leave meet')
                try:
                    driver.execute_script("document.getElementById('hangup-button').click()")
                    logging.debug('Clicked hangup button')
                    sleep(3)
                except:
                    logging.debug('Clicking hangup failed')
                finally:
                    leave_process(driver, process, sink_name)
                    return
            elif number_of_attendees == 0:
                roster_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["roster_btn"], 2)
                try:
                    driver.execute_script("arguments[0].click();", roster_btn)
                    logging.debug('Clicked roster btn')
                except:
                    logging.debug("Couldn't click roster btn")
            elif number_of_attendees > len(participant_list):
                # people = wait_and_find_elements_by_xpath(driver, properties["xpath"]["participant_list"])
                people = wait_and_find_elements_by_xpath(driver, properties["xpath"]["num_participants"])
                participant_list = [re.sub(r'\n.+', '', x.text).replace(' (Guest)', '') for x in people]
        else:
            roster_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["roster_btn"], 2)
            if roster_btn:
                continue
            logging.info('Meet ended/removed from meet')
            leave_process(driver, process, sink_name)
            return



def wait_for_meet_to_start(driver: webdriver.Chrome, sink_name: str, display: Display):
    """
    starts recording after the bot has joined the meet and returns the process
    """
    while True:
        roster_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["roster_btn"], 3)
        # roster btn to see list of attendees
        if roster_btn:
            process = record_meet(sink_name)
            return process
        in_lobby_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["in_lobby_text"], 3)
        if in_lobby_text:
            logging.info('Waiting in lobby')
            sleep(5)
        else:
            roster_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["roster_btn"], 2)
            if roster_btn:
                process = record_meet(sink_name)
                return process
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
    display = Display(visible=False, size=(1024, 576))
    display.start()

    opt = get_chrome_options(allow_cam_mic=True)
    opt.add_argument("--window-size=1024,576")
    opt.add_argument("--lang=en-GB")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opt)
    logging.debug('Driver started')
    driver.get(url)
    logging.debug(f'{url} opened')
    
    # # jugaad for bypassing 'open in app' prompt
    # driver.execute_script('window.open()')
    # driver.switch_to.window(driver.window_handles[1])
    # driver.get(url)    

    try:

        create_virtual_sink(output)

        join_meet(driver, output)

        process = wait_for_meet_to_start(driver, output, display)

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