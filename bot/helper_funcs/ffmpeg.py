#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Shrimadhav U K

# the logging things
import logging
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
LOGGER = logging.getLogger(__name__)

import asyncio
import os
import time
import re
import json
import subprocess
import math
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from bot.helper_funcs.display_progress import (
  TimeFormatter,
)
from bot.localisation import Localisation
from bot import (
    FINISHED_PROGRESS_STR,
    UN_FINISHED_PROGRESS_STR
)

async def convert_video(video_file, output_directory, total_time, bot, message):
    # https://stackoverflow.com/a/13891070/4723940
    out_put_file_name = output_directory + \
        "/" + str(round(time.time())) + ".mp4"
    progress = output_directory + "/" + "progress.txt"
    with open(progress, 'w') as f:
      pass
    file_genertor_command = [
      "ffmpeg",
      "-hide_banner",
      "-loglevel",
      "quiet",
      "-progress",
      progress,
      "-i",
      video_file,
      "-c:v",
      "libx265",
      "-preset", 
      "ultrafast",
      "-c:a",
      "copy",
      "-async",
      "1",
      "-strict",
      "-2",
      out_put_file_name
    ]
    
    process = await asyncio.create_subprocess_exec(
        *file_genertor_command,
        # stdout must a pipe to be accessible as process.stdout
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    LOGGER.info("ffmpeg_process: "+str(process.pid))
    status = output_directory + "/status.json"
    with open(status, 'r+') as f:
      statusMsg = json.load(f)
      statusMsg['pid'] = process.pid
      statusMsg['message'] = message.message_id
      f.seek(0)
      json.dump(statusMsg,f,indent=2)
    # os.kill(process.pid, 9)
    prevFrame = 0
    sameFrame = 0
    while True:
      await asyncio.sleep(3)
      with open("/app/DOWNLOADS/progress.txt",'r+') as file:
        text = file.read()
        frame = re.findall("frame=(\d+)", text)
        time_in_us=re.findall("out_time_ms=(\d+)", text)
        progress=re.findall("progress=(\w+)", text)
        speed=re.findall("speed=(\d+\.?\d*)", text)
        if len(frame):
          frame = int(frame[-1])
        else:
          frame = 1;
        if frame == prevFrame:
          LOGGER.info(frame)
          sameFrame += 1
        if sameFrame > 10:
          LOGGER.info(frame)
          return None
        prevFrame = frame
        if len(speed):
          speed = speed[-1]
        else:
          speed = 1;
        if len(time_in_us):
          time_in_us = time_in_us[-1]
        else:
          time_in_us = 1;
        if len(progress):
          if progress[-1] == "end":
            LOGGER.info(progress[-1])
            break
        else:
          LOGGER.info('no progress')
          
        elapsed_time = int(time_in_us)/1000000
        ETA = math.floor( (total_time - elapsed_time) / float(speed) )
        LOGGER.info(TimeFormatter(ETA*1000))
        percentage = math.floor(elapsed_time * 100 / total_time)
        progress_str = "[{0}{1}] \nP: {2}%\n".format(
            ''.join([FINISHED_PROGRESS_STR for i in range(math.floor(percentage / 5))]),
            ''.join([UN_FINISHED_PROGRESS_STR for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))
        try:
          #processing = Localisation.COMPRESS_PROGRESS.replace('{}', TimeFormatter(ETA*1000), 1).replace('{}', percentage, 2)
          await message.edit_text(
            text="🗜️ Compressing\n\n⏳ ETA: "+TimeFormatter(ETA*1000)+"\n\n"+progress_str
          )
        except:
            pass
        
    # Wait for the subprocess to finish
    stdout, stderr = await process.communicate()
    e_response = stderr.decode().strip()
    t_response = stdout.decode().strip()
    if os.path.lexists(out_put_file_name):
        return out_put_file_name
    else:
        return None

async def media_info(saved_file_path):
  process = subprocess.Popen(
    [
      'ffmpeg', 
      "-hide_banner", 
      '-i', 
      saved_file_path
    ], 
    stdout=subprocess.PIPE, 
    stderr=subprocess.STDOUT
  )
  stdout, stderr = process.communicate()
  output = stdout.decode().strip()
  duration = re.search("Duration:\s*(\d*):(\d*):(\d+\.?\d*)[\s\w*$]",output)
  bitrates = re.search("bitrate:\s*(\d+)[\s\w*$]",output)
  
  if duration is not None:
    hours = int(duration.group(1))
    minutes = int(duration.group(2))
    seconds = math.floor(float(duration.group(3)))
    total_seconds = ( hours * 60 * 60 ) + ( minutes * 60 ) + seconds
  else:
    total_seconds = None
  if bitrates is not None:
    bitrate = bitrates.group(1)
  else:
    bitrate = None
  return total_seconds, bitrate
    
