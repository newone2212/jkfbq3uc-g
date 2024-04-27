# Contents
- [Overview](#overview)
- [Meet script walkthrough](#meet-script-walkthrough)
- [Which libraries and packages are used and why?](#which-libraries-and-packages-are-used-and-why)
- [Other important things](#other-important-things)


### [Documentation video link](https://youtu.be/q7EoKNQ4gfI)

## Overview
- Using selenium chrome webdriver, the meet link is opened.
- A virtual audio device is created using [pulseaudio](https://www.freedesktop.org/wiki/Software/PulseAudio/) and later selected as speaker via meet settings.
- Bot waits until meet starts and starts recording system audio through the virtual audio device earlier created.
- Bot exits and kills processes after meet ends.

## Meet script walkthrough
- The API identifies which meet link is requested(Google Meet or MS-Teams etc.).
- Once identified the respective meet script is executed.
- As this code needs to run on a headless server, we use [PyVirtualDisplay](https://github.com/ponty/PyVirtualDisplay) which allows us to run apps headless within python. I didn't use the `--headless` option within chrome because with that I couldn't perform the click actions and also many other SSL cert issues, etc.
- Using [webdriver_manager](https://github.com/SergeyPirogov/webdriver_manager), we download and use the latest google-chrome webdriver. Google chrome was used instead of any other browser because most meet-providers optimize their sites for google-chrome.
- As multiple meetings need to run simultaneously, it's necessary to route every meeting through a separate speaker as while recording the audio we want separate meet's audio in separate files.
- Thus [pulseaudio](https://www.freedesktop.org/wiki/Software/PulseAudio/) is used to create a virtual audio device using this CLI command -> `pacmd load-module module-null-sink sink_name=Virtual_Sink sink_properties=device.description=Virtual_Sink`
- Now that we have a virtual speaker, we are ready to start the meet-joining process.
- To perform all click options via selenium, the elements are located via their xpath and these xpaths are defined in their respective properties file. Eg:- xpaths for google meet are defined in `google_meet_properties.json`.
- For google meet, we initially login via the acta google login because it's necessary to login before opening a meet link via selenium. Similarly for airmeet, we login using airmeet's login.
- Now, the meet url can be opened but for zoom the meet url needs to modified a bit to bypass the open in web browser dialog.
- Once the meet url is opened, we switch off the mic and camera via the meet options. This isn't really required as it's going to run on a server but is always better to do.
- Next step is to change the audio device to the newly created audio device. This is a MUST-DO step.
- This can be done by via 
    - the in-meet speaker settings.
    - routing the audio from the particular chrome process to the virtual audio device using pulseaudio.
- For airmeet the audio needed to be changed using the 2nd method given above due to a bug at their end which they hadn't solved.
- If using the 2nd method to change the audio device, the bot should initially join the meet and then change the audio device.
- If using the 1st method to change the audio device, the bot should initially change the audio device and then join the meet.
- Once the bot has changed the audio device, now the bot can join meet or send a request to join.
- If the bot is denied entry, the bot exits after removing the virtual audio device created earlier using this CLI command `pactl list short modules | grep "sink_name={sink_name}" | cut -f1 | xargs -L1 pactl unload-module`
- After the bot has joined the meet, the recording process starts using the CLI command `parec -d {output_name}.monitor | lame -r -V0 - ./recordings/{output_name}`
- The bot now checks after regular intervals whether the meet is active.
- Using the in-meet attendee tab, the attendee list is updated after regular intervals to later generate a CSV file of attendees in the meet.
- Once the meet ends or the bot is the only one remaining or the bot is removed, the following is done:- the recording process is killed, the virtual audio device is removed, the chrome webdriver is killed, the virtual display is stopped and the CSV file is generated.
- After execution of the script, the API then makes a post request of either success or failure.

## Which libraries and packages were used and why?

- [FastAPI](https://github.com/tiangolo/fastapi)
    - To implement the REST API to call the meet scripts via acta.ai's web tool.
    - Has better performance than flask/django.
- [Selenium](https://github.com/SeleniumHQ/selenium)
    - To automate the chrome tab handling the meet.
- [webdriver_manager](https://github.com/SergeyPirogov/webdriver_manager)
    - To download the latest google-chrome webdriver.
- [PyVirtualDisplay](https://github.com/ponty/PyVirtualDisplay)
    - To implement headless.
- [psutil](https://github.com/giampaolo/psutil)
    - To get the process ids of chrome tabs.
    - Used it to change the audio device via pulseaudio which requires the process id of the process with audio.
- [pulseaudio](https://www.freedesktop.org/wiki/Software/PulseAudio/)
    - To create and remove virtual audio devices
    - To record audio from the virtual audio device
    - To route audio from processes to the virtual audio device


## Other important things

- `main.py` file has the FastAPI code.
- `README.md` has setup and prerequisite info.
- Individual meet scripts are in `meet_scripts` folder. `helper_functions.py` has functions common for all meet scripts.
