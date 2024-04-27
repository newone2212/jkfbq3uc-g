import os
import subprocess
from time import sleep
from argparse import ArgumentParser, SUPPRESS
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import psutil

# To install dependencies for pyvirtualdisplay required for headless fire below command:-
# sudo apt-get install xvfb xserver-xephyr tigervnc-standalone-server xfonts-base

# fire below command for installing recording package
# sudo apt-get install pulseaudio-utils lame mpg123


sleepDelay = 2  # increase if you have a slow internet connection
timeOutDelay = 10

logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


def parse_arguments():
    '''
    argument parser code
    '''
    parser = ArgumentParser(description='Record meet given a link and name of output file', add_help=False)
    required = parser.add_argument_group('required arguments')
    optional = parser.add_argument_group('optional arguments')
    # Add back help 
    optional.add_argument(
        '-h',
        '--help',
        action='help',
        default=SUPPRESS,
        help='show this help message and exit'
    )
    required.add_argument('-u', '--url', type=str, required=True, help='Meet URL')
    required.add_argument('-o', '--output_file', type=str, required=True, help='Output file name, eg:- out.wav')
    args = parser.parse_args()
    return args


def get_chrome_options(allow_cam_mic: bool = True) -> Options:
    '''
    sets options for chrome and returns it
    '''
    opt = Options()
    opt.add_argument("--disable-default-apps")
    opt.add_argument("--disable-infobars")
    opt.add_argument("start-maximized")
    opt.add_argument("--disable-extensions")
    opt.add_argument(
        'useragent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36')
    opt.add_argument("--lang=en-GB")
    permission_value = 1
    if not allow_cam_mic:
        permission_value = 2
    # Pass the argument 1 to allow and 2 to block
    opt.add_experimental_option("prefs", {"profile.default_content_setting_values.media_stream_mic": permission_value,
                                        "profile.default_content_setting_values.media_stream_camera": permission_value,
                                        "profile.default_content_setting_values.notifications": permission_value
                                        })
    return opt


def wait_and_find_element_by_xpath(driver: webdriver.Chrome, xpath: str, timeout=timeOutDelay):
    '''
    returns the first element found with the given xpath
    '''
    sleep(sleepDelay)
    for i in range(timeout):
        try:
            ele = driver.find_element_by_xpath(xpath)
        except:
            sleep(sleepDelay)
        else:
            return ele

def wait_and_find_elements_by_xpath(driver: webdriver.Chrome, xpath: str, timeout=timeOutDelay):
    '''
    returns a list of elements with the given xpath
    '''
    sleep(sleepDelay)
    for i in range(timeout):
        try:
            ele = driver.find_elements_by_xpath(xpath)
        except:
            sleep(sleepDelay)
        else:
            return ele

def record_meet(output: str):
    '''
    fires a cli command to record system audio:-
    parec -d <device> | lame -r -V0 - <output_file.mp3>

    To find <device> by firing following command and choosing output device:-
    pacmd list-sources | grep -e 'name:' -e 'index' -e 'Speakers'
    '''
    command = f'parec -d {output}.monitor | lame -r -V0 - ./recordings/{output}'
    process = subprocess.Popen(command, shell=True, preexec_fn=os.setsid)
    logging.info(f'Started recording to {output}')
    return process


def create_virtual_sink(sink_name: str) -> None:
    '''
    Creates a virtual sink (speaker) using pulseaudio to route every meeting through a unique speaker
    '''
    command = ['pacmd', 'load-module', 'module-null-sink', f'sink_name={sink_name}', f'sink_properties=device.description={sink_name}']
    subprocess.run(command)
    logging.info(f'Created virtual sink: {sink_name}')


def remove_virtual_sink(sink_name: str) -> None:
    '''
    Removes the virtual sink earlier created
    '''
    # when using grep or pipe you need to use shell=True and pass command as a string
    command = f'pactl list short modules | grep "sink_name={sink_name}" | cut -f1 | xargs -L1 pactl unload-module'
    subprocess.run(command, shell=True)
    logging.info(f'Removed virtual sink: {sink_name}')


def move_sink_input(stream_id: str, sink_name: str) -> bool:
    """
    Moves the specified playback stream output to the specified sink. Using     
    `$pactl move-sink-input 250 Virtual_Sink_Name` where 250 is the numerical index 
    (Sink Input # in pactl list sink-inputs) of the stream. Returns True on success else False
    """
    mv_cmnd = ['pactl', 'move-sink-input', stream_id, sink_name]
    process = subprocess.run(mv_cmnd)
    if process.returncode == 0:
        logging.info(f'Successfully moved Sink Input #: {stream_id} to {sink_name}')
    else:
        logging.error('Failed to move sink input')
    return process.returncode == 0


def get_sink_inputs() -> dict:
    """
    Returns a dict() with key as pid and value as index
    """
    cmnd = r"""pacmd list-sink-inputs | perl -0777pe's/ *index: (\d+).+?application\.process\.id = "([^\n]+)"\n.+?(?=index:|$)/$2:$1\n/sag'"""
    process = subprocess.run(cmnd, shell=True, stdout=subprocess.PIPE)
    if process.returncode == 1:
        logging.error('Failed to get sink inputs')
        return None
    input_dict = dict()
    ls = process.stdout.decode('utf-8').rstrip().split('\n')[1:]
    if len(ls) == 0:
        logging.error('Failed to get sink inputs')
        return None
    for e in ls:
        e_split = e.split(':')
        input_dict[int(e_split[0])] = e_split[1]
    logging.debug('Got sink inputs')
    return input_dict


def get_chrome_child_processes_pids(driver: webdriver.Chrome) -> list:
    """
    returns list of pid's of chrome webdriver's processes
    """
    ls = [p.pid for p in psutil.Process(driver.service.process.pid).children(recursive=True)]
    return ls


def change_audio_device(driver: webdriver.Chrome, sink_name: str) -> bool:
    """
    Changes the audio device for the webdriver to given sink and returns True if successfull
    """
    sink_dict = get_sink_inputs()
    if sink_dict is None:
        logging.error('sink dict is none')
        return False
    process_list = list(set(sink_dict.keys()).intersection(get_chrome_child_processes_pids(driver)))
    if len(process_list) == 0:
        logging.error('Failed to move sinks')
        return False
    for pid in process_list:
        move_sink_input(sink_dict[pid], sink_name)
    logging.debug('Moved all sinks')
    return True


def start_pulseaudio():
    process = subprocess.run(['pulseaudio', '--start'])
    if process.returncode == 0:
        logging.info('Started pulseaudio')