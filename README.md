# acta-demo
Takes the ms-teams meeting link and name of output file as cli arguments and records the meeting.
## Tested only on Ubuntu and RHEL 8 for Python3.8

## Prerequisites:
- Step 0:

  Clone repo
  ```bash
  git clone https://github.com/atharva-lipare/acta-demo.git
  ```
  Create recordings folder inside acta-demo folder
  ```bash
  cd acta-demo
  mkdir recordings
  ```
- Step 1:

  To install python3.8 & pip3.8 for ubuntu
  ```bash
  sudo apt-get update

  sudo apt install software-properties-common
  
  sudo add-apt-repository ppa:deadsnakes/ppa
  
  sudo apt install python3.8
  
  sudo apt install python3-pip
  ```
  To install python3.8 & pip3.8 for RHEL https://tecadmin.net/install-python-3-8-centos/
  ```bash
  sudo yum update
  sudo yum install gcc openssl-devel bzip2-devel libffi-devel python3-devel
  cd /opt
  sudo wget https://www.python.org/ftp/python/3.8.7/Python-3.8.7.tgz

  sudo tar xzf Python-3.8.7.tgz

  cd Python-3.8.7

  sudo ./configure --enable-optimizations

  sudo make altinstall

  sudo rm Python-3.8.7.tgz

  python3.8 -V
  ```
- Step 2:
  
  To install dependencies for ubuntu
  ```bash
  sudo apt-get update

  sudo apt-get install xvfb xserver-xephyr tigervnc-standalone-server xfonts-base pulseaudio-utils lame mpg123 libasound2 libasound2-plugins alsa-utils alsa-oss pulseaudio pulseaudio-utils
  ```
  To install dependencies for RHEL 8
  ```bash
  sudo yum install xorg-x11-server-Xvfb.x86_64 xorg-x11-server-Xephyr.x86_64 pulseaudio-utils.x86_64 lame-libs.x86_64 mpg123.x86_64 alsa-utils pulseaudio
  ```
  Intall Lame - Follow this: Question itself is the answer.
  https://serverfault.com/questions/808821/installing-lame-on-amazon-linux-command-not-found  

- Step 3:
  
  To install python3 dependencies
  ```bash
  pip3.8 install -r requirements.txt
  
  #if ps utils gives and error
  yum install -y python38 python38-devel
  
  ```
  
- Step 4:
  
  To install Google Chrome Headless Ubuntu
  ```bash
  sudo apt-get update
  sudo apt-get install -y libappindicator1 fonts-liberation
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  sudo dpkg -i google-chrome*.deb
  ```
  To install Google Chrome for RHEL
  ```bash
  wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm

  sudo yum -y localinstall google-chrome-stable_current_x86_64.rpm
  ```
- Step 5:

  To run Pulse Audio https://askubuntu.com/questions/28176/how-do-i-run-pulseaudio-in-a-headless-server-installation
  ```bash
  sudo usermod -aG pulse,pulse-access <user-name>   #Set Group Memberships for PA:
  pulseaudio -D #Run the PulseaudioServer:
  pacmd list-sinks # test if pacmd working
  ```
- Step 6:

  To install dependency for fastapi
  ```bash
  pip3.8 install -U setuptools
  pip3.8 install uvicorn[standard]
  ```
- Step 7:
  Install s3fs 
  Recording Server: https://cloud.netapp.com/blog/amazon-s3-as-a-file-system
  ACTA Server: https://medium.com/tensult/aws-how-to-mount-s3-bucket-using-iam-role-on-ec2-linux-instance-ad2afd4513ef
  ```bash
  On Linux box:
  sudo s3fs twillio-meetings-recordings  -o use_cache=/tmp -o allow_other -o uid=500 -o mp_umask=007 -o multireq_max=10 /mnt/s3/twillio-meetings-recordings/
  
  On Recording box follow the link
  ```

## Run the app
- To run the API in the background, run this command in current dir
  ```bash
  nohup uvicorn main:app &
  ```
- To run in terminal
  ```bash
  uvicorn main:app
  ```
# REST API

## Join Meet And monitor
`POST /meet/{meet_id}`
### Request URL
`http://127.0.0.1:8000/meet/{meet_id}/?url=encoded-url&outputFile=fileName.flac`
#### Parameters
- url: Encoded meeting URL
- outputFile: File name with flac, mp3, wav extensions

After succesfull completion will send a post request to:-
`https://api.acta.ai/hello/meetings/12345/roboRecordingAvailable?success=true` else on failure at `?success=false` 

Eg:- `http://127.0.0.1:8000/meet/12345/?url=https%3A%2F%2Fmeet.google.com%2Fogo-abcd-nkj&outputFile=out.flac`

## To run individual meeting scripts:
  ```bash
  usage: python3 <script.py> [-h] -u URL -o OUTPUT_FILE

  Record meet given a link and name of output file

  required arguments:
    -u URL, --url URL     Meet URL
    -o OUTPUT_FILE, --output_file OUTPUT_FILE
                          Output file name, eg:- out.wav

  optional arguments:
    -h, --help            show this help message and exit

  ```
  Example:-
  ```bash
  python3.8 ms_teams_join.py -u https://teams.live.com/meet/123 -o out1.wav
  ```
  ```bash
  python3.8 google_meet_join.py -u https://meet.google.com/abc-defg-hij -o out1.wav
  ```
## Useful Info
- Meet recordings and attendee list are stored in recordings/
- logs are created in app.log
- If running script on new instance and script failing after google sign in, run following in Python interactive shell to register new device after google_sign_in():-
  ```bash
  wait_and_find_element_by_xpath(driver, "//input[@type='tel']").send_keys('+91<mobile-number>')
  wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphonecollectNext"]/div/button/span').click()
  wait_and_find_element_by_xpath(driver, "//input[@type='tel']").send_keys('<OTP>')
  wait_and_find_element_by_xpath(driver, '//*[@id="idvanyphoneverifyNext"]/div/button/span').click()
  ```
"# jkfbq3uc-g" 
