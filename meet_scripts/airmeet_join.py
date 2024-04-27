import logging
import os
import signal
import sys
import traceback
from time import sleep
import json
import csv

# To install dependencies for pyvirtualdisplay required for headless fire below command:-
# sudo apt-get install xvfb xserver-xephyr tigervnc-standalone-server xfonts-base
from pyvirtualdisplay import Display

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from helper_functions import *

# fire below command for installing recording package
# sudo apt-get install pulseaudio-utils lame mpg123

has_audio_changed = False
participant_list = list()


logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

try:
    with open('./meet_scripts/airmeet_properties.json', 'r') as f:
        properties = json.load(f)
except:
    logging.error('failed to open airmeet_properties.json')
    sys.exit(1)


def login(driver):
    """
    login using airmeet credentials
    """
    login_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["login_btn"])
    login_btn.click()
    logging.debug('Clicked login btn')
    email_input = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_input"])
    email_input.send_keys(properties["login"]["email_id"])
    logging.debug('Entered email_id')
    email_continue_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["email_continue_btn"])
    email_continue_btn.click()
    logging.debug('Clicked continue btn')
    password_input = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_input"])
    password_input.send_keys(properties["login"]["password"])
    logging.debug('Entered password')
    password_login_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["password_login_btn"])
    password_login_btn.click()
    logging.debug('Clicked login btn')


def kill_driver_sink(driver: webdriver.Chrome, sink_name: str, display: Display):
    """
    function to kill driver, sink, display
    """
    driver.quit()
    logging.debug('Driver closed')
    remove_virtual_sink(sink_name)
    display.stop()


def has_event_started(driver: webdriver.Chrome, sink_name: str, display: Display) -> bool:
    """
    returns boolean whether event has started
    """
    if wait_and_find_element_by_xpath(driver, properties["xpath"]["event_started_text"], 2):
        return True
    elif wait_and_find_element_by_xpath(driver, properties["xpath"]["event_ended_text"], 2):
        logging.info('Event has ended. Preparing to exit')
        kill_driver_sink(driver, sink_name, display)
        logging.info('SUCCESS: Exiting script with ret code 0')
        sys.exit(0)
    else:
        return False


def wait_for_event_to_start(driver: webdriver.Chrome, url: str, sink_name: str, display: Display) -> None:
    """
    Waits for event to start
    """
    while True:
        if has_event_started(driver, sink_name, display):
            logging.info('Event has started. Preparing to join meet')
            return
        driver.get(url)
        sleep(5)


def enter_event(driver: webdriver.Chrome, audio_device: str) -> None:
    continue_btn = wait_and_find_element_by_xpath(driver, "//*[text()='Continue']", 3)
    try:
        continue_btn.click()
        logging.debug('Clicked continue btn')
    except:
        logging.debug('Failed to click continue btn')
    enter_event_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["enter_event_btn"],3)
    try:    
        enter_event_btn.click()
        logging.debug('Clicked enter event btn')
    except:
        logging.warning('Failed to click enter event')
    enter_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["enter_btn"],3)
    try:
        enter_btn.click()
        logging.debug('Clicked enter btn')
    except:
        logging.warning('Failed to click enter')
    #choose_audio_device(driver, audio_device) # Can use this function after airmeet fixes the bug at their end
    enter_venue_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["enter_venue_without_mic"])
    enter_venue_btn.click()
    logging.debug('Clicked Enter venue btn')


#def choose_audio_device(driver: webdriver.Chrome, audio_device: str) -> None:
#    """
#    Chooses custom virtual audio device as speaker. But this doesn't work due to a bug at their end. 
#    """
#    test_speaker_mic_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["test_speaker_mic_btn"])
#    test_speaker_mic_btn.click()
#    logging.debug('Clicked Test speaker and mic btn')
#    speaker_dropdown = wait_and_find_elements_by_xpath(driver, '//*[@id="dropdownMenuLink"]')[-1]
#    speaker_dropdown.click()
#    logging.debug('Clicked speaker dropdown')
#    sleep(2)
#    audio_device_entry = wait_and_find_element_by_xpath(driver, f"//span[contains(text(), '{audio_device}')]")
#    audio_device_entry.click()
#    logging.debug('Selected custom audio device')
#    #sleep(20)
#    audio_settings_close_btn = wait_and_find_element_by_xpath(driver, '//button[@class="close btn-close"]')
#    audio_settings_close_btn.click()
#    logging.debug('Clicked close settings btn')


def get_session_status(driver: webdriver.Chrome) -> str:
    """
    returns session status:- ['completed', 'not started', 'started', 'paused'] after clicking view schedule btn
    """
    schedule_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["schedule_text"], 5)
    if not schedule_text:
        if wait_and_find_element_by_xpath(driver, properties["xpath"]["after_meet_rating"], 2) is not None:
            return "completed"
        view_schedule_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["view_schedule_btn"])
        if view_schedule_btn:
            try:
                view_schedule_btn.click()
                logging.debug('Clicked view schedule button')
            except:
                return "not started"
        else:
            return "not started"
    is_started = wait_and_find_element_by_xpath(driver, properties["xpath"]["live_text"], 2)
    if is_started:
        return "started"
    is_paused = wait_and_find_element_by_xpath(driver, properties["xpath"]["paused_text"], 2)
    if is_paused:
        return "paused"
    is_completed = wait_and_find_element_by_xpath(driver, properties["xpath"]["completed_text"], 2)
    if is_completed:
        return "completed"    
    return "not started"


def wait_for_session_to_start(driver: webdriver.Chrome, sink_name: str, display: Display) -> None:
    """
    Waits to start recording until session has started
    """
    while True:
        session_status = get_session_status(driver)
        if session_status == 'started':
            return
        #elif session_status in ['completed', 'paused']:
        #    kill_driver_sink(driver, sink_name, display)
        sleep(5)


def get_number_of_attendees(driver: webdriver.Chrome) -> int:
    """
    returns the number of attendees
    """
    show_ppl_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["show_people_btn"])
    if show_ppl_btn:
        num_people_text = wait_and_find_element_by_xpath(driver, properties["xpath"]["num_people_text"])
        if num_people_text:
            num_people_text = num_people_text.text
            num_people_text = num_people_text[num_people_text.find('(')+1:-1]
            if num_people_text.isdecimal():
                return int(num_people_text)
        else:
            try:
                driver.execute_script('''document.evaluate("//p[text()='People']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()''')
                #show_ppl_btn.click() # don't use this because above line allows it to open schedule and people tab simultaneously
                logging.debug('Clicked show people button')
            except:
                logging.warning('Failed to click show people button')
    return 0


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


def update_participant_list(driver: webdriver.Chrome):
    """
    Updates the participant list of number of attendees increases
    """
    global participant_list
    people_list = wait_and_find_elements_by_xpath(driver, properties["xpath"]["people_list"], 2)
    if people_list:
        if len(people_list) > len(participant_list):
            participant_list = [attendee.text[:attendee.text.find('\n')] for attendee in people_list]
            logging.debug('Updated participant list')
    else:
        show_ppl_btn = wait_and_find_element_by_xpath(driver, properties["xpath"]["show_people_btn"])
        if show_ppl_btn:
            try:
                show_ppl_btn.click()
                logging.debug('Clicked show people button')
            except:
                logging.warning('Failed to click show people button')


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


def check_if_meet_active(driver: webdriver.Chrome, process: subprocess.Popen, sink_name: str):
    """
    decides whether to keep bot active or to leave
    """
    global has_audio_changed
    while True:
        if not has_audio_changed:
            change_audio_device(driver, sink_name)
            has_audio_changed = True
        session_status = get_session_status(driver)
        if session_status == 'completed':
            leave_process(driver, process, sink_name)
            logging.debug('Meet ended, preparing to leave')
            return
        num_attendees = get_number_of_attendees(driver)
        if num_attendees == 1:
            leave_process(driver, process, sink_name)
            logging.debug('Bot only one in meet, thus leaving')
            return
        experience_dialog = wait_and_find_element_by_xpath(driver, properties["xpath"]["after_meet_rating"], 1)
        if experience_dialog:
            leave_process(driver, process, sink_name)
            logging.debug('Meet ended, preparing to leave')
            return
        update_participant_list(driver)
        sleep(5)


def switch_to_audio_only_mode(driver: webdriver.Chrome):
    """
    switches to audio only mode within airmeet to save internet usage
    """
    try:
        driver.execute_script('''document.evaluate("//*[text()='Audio Only Mode']", document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.click()''')
        logging.debug('Switched to audio only mode')
    except:
        logging.warning('Failed to switch to audio only mode')


def main(url: str, output: str) -> None:

    start_pulseaudio()

    # start virtual display for headless
    display = Display(visible=0, size=(1366, 868))
    display.start()

    opt = get_chrome_options(allow_cam_mic=False)
    opt.add_argument("--window-size=1366,868")
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=opt)
    logging.debug('Driver started')

    try:

        create_virtual_sink(output)
        driver.get(url)       

        if not has_event_started(driver, output, display):
            wait_for_event_to_start(driver, url, output, display)
        
        login(driver)
        logging.debug('Succesfully logged in')
        
        enter_event(driver, output)
        logging.debug('Entered event')

        wait_for_session_to_start(driver, output, display)
        logging.debug('Session started')

        process = record_meet(output)

        switch_to_audio_only_mode(driver)

        check_if_meet_active(driver, process, output)

        display.stop()

        logging.info('SUCCESS: Exiting script with ret code 0')
        sys.exit(0)

    except Exception as e:
        traceback.print_exc()
        try:            
            driver.quit()
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
