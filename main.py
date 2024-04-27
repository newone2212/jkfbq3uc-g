from fastapi import FastAPI, Query, status, HTTPException
from pydantic import AnyHttpUrl, FilePath
import os
import subprocess
import threading
import logging
import httpx

logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

app = FastAPI()

def get_return_code(process, outputFile):
    '''
    monitors the process and sends a post request upon completion
    '''
    process.communicate()[0]
    if process.returncode == 0:
        post_url = 'https://api.acta.ai/hello/roboRecordingAvailable?success=true&roboFileName=' + outputFile;
        r = httpx.post(url=post_url)
        logging.info(f'Sent post request: {post_url} with respose: {r}')
    elif process.returncode == 1:
        post_url = 'https://api.acta.ai/hello/roboRecordingAvailable?success=false&roboFileName=' + outputFile;
        r = httpx.post(url=post_url)
        logging.info(f'Sent post request: {post_url} with response {r}')


# pass encoded url using encodeURIComponent()
@app.post("/api/meet", status_code=status.HTTP_201_CREATED)
async def join_meet_and_monitor(
    url: AnyHttpUrl = Query(
        ...,
        title="Meet URL",
        description="Encoded meeting URL"
    ),
    outputFile: str = Query(
        ...,
        title="File name",
        description="File name with flac, mp3, wav extensions",
        regex="^.*\.(flac|mp3|wav)$"
    )
):
    if "teams." in url:
        logging.info('ms teams url found')
        process = subprocess.Popen(['python3.8', './meet_scripts/ms_teams_join.py', '-u', url, '-o', outputFile], cwd=os.path.dirname(os.path.realpath(__file__)), preexec_fn=os.setsid)
        thread = threading.Thread(target=get_return_code, args=(process,outputFile,))
        thread.start()
        return {"meet_url": url, "file_name": outputFile, "site": "MS Teams"}
    elif "meet.google.com" in url:
        logging.info('google meet url found')
        process = subprocess.Popen(['python3.8', './meet_scripts/google_meet_join.py', '-u', url, '-o', outputFile], cwd=os.path.dirname(os.path.realpath(__file__)), preexec_fn=os.setsid)
        thread = threading.Thread(target=get_return_code, args=(process,outputFile,))
        thread.start()
        return {"meet_url": url, "file_name": outputFile, "site": "Google Meet"}
    elif "airmeet" in url:
        logging.info('airmeet url found')
        process = subprocess.Popen(['python3.8', './meet_scripts/airmeet_join.py', '-u', url, '-o', outputFile], cwd=os.path.dirname(os.path.realpath(__file__)), preexec_fn=os.setsid)
        thread = threading.Thread(target=get_return_code, args=(process,outputFile,))
        thread.start()
        return {"meet_url": url, "file_name": outputFile, "site": "Airmeet"}
    elif "zoom.us/j/" in url:
        logging.info('zoom url found')
        process = subprocess.Popen(['python3.8', './meet_scripts/zoom_join.py', '-u', url, '-o', outputFile], cwd=os.path.dirname(os.path.realpath(__file__)), preexec_fn=os.setsid)
        thread = threading.Thread(target=get_return_code, args=(process,outputFile,))
        thread.start()
        return {"meet_url": url, "file_name": outputFile, "site": "Zoom"}
    elif "gotomeet" in url:
        logging.info('GoToMeeting url found')
        process = subprocess.Popen(['python3.8', './meet_scripts/gotomeet_join.py', '-u', url, '-o', outputFile], cwd=os.path.dirname(os.path.realpath(__file__)), preexec_fn=os.setsid)
        thread = threading.Thread(target=get_return_code, args=(process,outputFile,))
        thread.start()
        return {"meet_url": url, "file_name": outputFile, "site": "GoToMeeting"}
    else:
        logging.warning(f'{url} not supported')
        raise HTTPException(status_code=404, detail="URL not supported")