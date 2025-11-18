import os
import subprocess
import sys

import numpy as np
from moviepy import concatenate_audioclips, concatenate_videoclips, VideoFileClip
import soundfile as sf


percent = 0.2  # percent of movie to keep    
around = 20    # number of seconds around peaks

_tmp = 'extract_loud.wav'


def convert_to_wav(videofile):
    try:
        os.remove(_tmp)
    except FileNotFoundError:
        pass

    cmd = 'ffmpeg -i %s -ab 160k -ac 2 -ar 44100 -vn %s' % (videofile, _tmp)
    subprocess.call(cmd, shell=True)
    return _tmp


def find_loud(wavfile):
    # Read wav file using soundfile
    sound, samplerate = sf.read(wavfile)
    msec = 1000
    frame_length = int(samplerate * (msec / 1000))  # frames per msec

    desired_len = percent * len(sound) / samplerate  # in seconds
    desired_peaks = int(desired_len / around) + 1

    # Calculate the max dBFS for each segment
    intervals = []
    for i in range(0, len(sound), frame_length):
        segment = sound[i:i + frame_length]
        max_db = 20 * np.log10(np.max(np.abs(segment)) + 1e-10)  # Avoid log(0)
        intervals.append((max_db, i / samplerate))

    print('all intervals', intervals)

    sorted_intervals = sorted(intervals, key=lambda x: x[0])

    print('sorted intervals', sorted_intervals)

    keep = []

    for db, i in sorted_intervals:
        start = max(0, i - int(around / 2))
        end = min(len(sound) / samplerate, i + int(around / 2))
        skip = False
        for intr in keep:
            if ((intr[0] >= start and intr[0] <= end) or
                (intr[1] >= start and intr[1] <= end)):
                skip = True
                break
        if skip:
            continue
        keep.append((start, end))
        if len(keep) >= desired_peaks:
            break

    keep = sorted(keep, key=lambda x: x[0])
    print('keeping these intervals of the video:', keep)

    return keep


def slice_loud(intervals, videofile, out):
    vid = VideoFileClip(videofile)
    vclips, aclips = [], []
    
    # Extract audio clips for corresponding intervals
    for intr in intervals:
        vclips.append(vid.subclipped(*intr))
        aclips.append(vid.audio.subclipped(*intr))

    full = concatenate_videoclips(vclips).with_audio(concatenate_audioclips(aclips))
    full.write_videofile(out,
                         codec='libx264',
                         audio_codec='aac',
                         temp_audiofile='temp-audio.m4a',
                         remove_temp=True)


if __name__ == '__main__':
    wav = convert_to_wav(sys.argv[1])
    try:
        clips = find_loud(wav)
        print('intervals', clips)
        slice_loud(clips, sys.argv[1], sys.argv[2])
    finally:
        os.remove(wav)
