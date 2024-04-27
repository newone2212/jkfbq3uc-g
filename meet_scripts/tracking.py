import threading
import json
from datetime import datetime, timedelta
import pandas as pd
import re

import logging
logging.basicConfig(filename='app.log',format='%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

class Speaker:
    def __init__(self, name, speaker_ideal_timeout=1.2, min_speaking_duration_seconds=0.5, verbose=False):
        self.name = name
        self.start_time = None
        self.last_update_time = None
        self.end_time = None
        self.speaker_ideal_timeout = timedelta(seconds=speaker_ideal_timeout)
        self.min_speaking_duration = timedelta(seconds=min_speaking_duration_seconds)
        self.verbose = verbose

    def start_session(self, current_time):
        self.start_time = current_time
        self.last_update_time = current_time
        self.end_time = None
        if self.verbose:
            logging.debug(f"[{current_time}] Starting session for {self.name}")

    def update(self, current_time):
        self.last_update_time = current_time
        if self.verbose:
            logging.debug(f"[{current_time}] Updating session for {self.name}")

    def is_active(self, current_time):
        return self.end_time is None and self.start_time is not None and (current_time - self.last_update_time <= self.speaker_ideal_timeout)

    def finalize(self, current_time):
        if current_time - self.last_update_time > self.speaker_ideal_timeout:
            self.end_time = self.last_update_time
            duration = self.end_time - self.start_time
            if duration >= self.min_speaking_duration:
                session_data = {
                    'start': self.start_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    'end': self.end_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    'speaker': self.name
                }
                
                logging.debug(f"[{current_time}] Finalizing session for {self.name}: {session_data}")
                print(f"[{current_time}] Finalizing session for {self.name}: {session_data}")
                
                return True, session_data
            else:
                session_data = {
                    'start': self.start_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    'end': self.end_time.strftime("%Y-%m-%d %H:%M:%S"), 
                    'speaker': self.name
                }
                
            
                logging.debug(f"[{current_time}] Finalizing failed session for {self.name} : {session_data}")
                print(f"[{current_time}] Finalizing failed session for {self.name} : {session_data}")
            
                return True, None
            # self.start_time = None
            # self.end_time = None
            
        return False, None

class SpeakerTracker:
    def __init__(self, driver, properties, verbose=False):
        self.driver = driver
        self.properties = properties
        self.active = False
        self.speakers = {}
        self.speakers_data = {}
        self.all_sessions = []
        self.verbose = verbose
        self.start_time = None
        self.end_time = None
        self.hits = 0

    def start_tracking(self):
        self.active = True
        self.start_time = datetime.now()
        self.tracking_thread = threading.Thread(target=self.track_speakers)
        self.tracking_thread.start()
        if self.verbose:
            logging.debug("[INFO] Tracking started.")

    def stop_tracking(self):
        self.active = False
        now = datetime.now()
        self.end_time = now
        for speaker in self.speakers.values():
            data = speaker.finalize(now)
            if data:
                self._add_speaker_data(speaker.name, data)
                self.all_sessions.append(data)
        self.tracking_thread.join()
        if self.verbose:
            logging.debug("[INFO] Tracking stopped.")
            logging.debug(f"[INFO] Recording speed {self.hits/(self.end_time - self.start_time).total_seconds()} per second")

    def track_speakers(self):
        prev = {}
        while self.active:
            self.hits+=1
            try:
                now = datetime.now()
                people = self.driver.find_elements_by_xpath(self.properties["xpath"]["people_list"])
                for p in people:
                    speaker_name = p.text
                    outer_html = p.get_attribute('outerHTML')
                    
                    if prev.get(speaker_name) != outer_html:
                        # if not self.speakers[speaker_name].is_active(now):
                        #     self.speakers[speaker_name].start_session(now)
                        if speaker_name not in self.speakers:
                            self.speakers[speaker_name] = Speaker(speaker_name, verbose=self.verbose)
                            self.speakers[speaker_name].start_session(now)
                        else:
                            if speaker.is_active(now):
                                self.speakers[speaker_name].update(now)
                    prev[speaker_name] = outer_html

                clear_speakers = []
                for name in self.speakers.keys():
                    speaker = self.speakers[name]
                    # if not speaker.is_active(now):
                    status, data = speaker.finalize(now)
                    if status:
                        if data:
                            self._add_speaker_data(name, data)
                            self.all_sessions.append(data)
                        clear_speakers.append(name)

                for name in clear_speakers:
                    del self.speakers[name]
            except Exception as e:
                logging.error("Exception\n")
                logging.debug(e)
                logging.debug("-"*50)
                logging.debug("-"*50)
                # raise

    def _add_speaker_data(self, name, data):
        if name not in self.speakers_data:
            self.speakers_data[name] = []
        self.speakers_data[name].append(data)

    def export_to_json(self, file_path):
        with open(file_path, 'w') as file:
            json.dump({'speakers_data': self.speakers_data, 'all_sessions': self.all_sessions}, file, indent=4)
        if self.verbose:
            logging.debug(f"[INFO] Data exported to {file_path}")

    def export_to_csv(self, file_path, meeting_start_time):
        
        # Create DataFrame directly from all_sessions
        df = pd.DataFrame(self.all_sessions)

        # Name formating
        df['speaker'] = df['speaker'].apply(lambda x: re.sub(r'\n.+', '', x).replace('keep_pin',''))

        # Convert start and end times to datetime
        df['start_dt'] = pd.to_datetime(df['start'], format="%Y-%m-%d %H:%M:%S")
        df['end_dt'] = pd.to_datetime(df['end'], format="%Y-%m-%d %H:%M:%S")

        # Calculate relative times
        df['start'] = (df['start_dt'] - meeting_start_time).dt.total_seconds()
        df['end'] = (df['end_dt'] - meeting_start_time).dt.total_seconds()

        # Get segment string
        df['segment'] = df.apply(lambda x: self._format_segment(x['start'], x['end']), axis=1)

        # Select and reorder columns
        df = df[['speaker', 'segment', 'start', 'end', 'start_dt', 'end_dt']]

        # Export to CSV
        df.to_csv(file_path, index=False)
        if self.verbose:
            logging.debug(f"[INFO] Data exported to {file_path} as CSV")

    def _format_segment(self, start_seconds, end_seconds):
        def format_time(seconds):
            hours, remainder = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = int((seconds - int(seconds)) * 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

        start_formatted = format_time(start_seconds)
        end_formatted = format_time(end_seconds)
        return f"[{start_formatted} --> {end_formatted}]"