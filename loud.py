import os
import subprocess
import sys

from pydub import AudioSegment
from moviepy.editor import AudioFileClip, VideoFileClip, \
    concatenate_videoclips as concat_video, \
    concatenate_audioclips as concat_audio

percent = .2  # percent of movie to keep    
around = 20   # number of seconds around around the peaks


_tmp = 'extract_loud.wav'


def convert_to_wav(videofile):
    if os.path.isfile(_tmp):
        os.remove(_tmp)

    cmd = 'ffmpeg -i %s -ab 160k -ac 2 -ar 44100 -vn %s' % (videofile, _tmp)
    subprocess.call(cmd, shell=True)
    return _tmp


def find_loud(wavfile):
    sound = AudioSegment.from_wav(wavfile)
    msec = 1000

    desired_len = percent * len(sound) / 1000
    desired_peaks = int(desired_len / around) + 1
    intervals = [(sound[i:i+msec].max_dBFS, i/1000) for i in range(0, len(sound), msec)]

    print('all intervals', intervals)

    sorted_intervals = list(intervals)
    sorted_intervals = sorted(sorted_intervals, key=lambda x: x[0])

    print('sorted intervals', sorted_intervals)

    keep = []

    for db, i in sorted_intervals:
        start = max(0, i-int(around/2))
        end = min(len(sorted_intervals)-1, i+int(around/2))
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
    vid, vclips, aclips = VideoFileClip(videofile), [], []
    for intr in intervals:
        vclips.append(vid.subclip(*intr))
        aclips.append(vid.audio.subclip(*intr))

    full = concat_video(vclips).set_audio(concat_audio(aclips))
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
