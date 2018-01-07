"""
Convert a large audio wav file (album length, i.e. > 30 minutes typically)
into a series of videos consisting of the audio synchronized with images of the
spectrogram.
"""
import os
import sys
import multiprocessing as mp
import subprocess

import tqdm
import numpy as np
import librosa.core
import librosa.display
import librosa.feature
import matplotlib.pyplot as plt
plt.switch_backend("agg")

SAMPLERATE = 44.1e3     # samples/sec
WAVPATH = sys.argv[1]
BASENAME = os.path.basename(WAVPATH).replace(".wav", "")
ROOT = "/mnt/nfs-share/music/data"
FRAMEROOT = ROOT + "/frames/" + BASENAME
DURATION = 20  #
NUMPROC = 8
FFTFREQ = librosa.fft_frequencies(sr=SAMPLERATE)
F_MAX = np.max(FFTFREQ)
N_FFT = 2048
N_HOP = int(1.0 / 4 * N_FFT)
FILETIME = librosa.core.get_duration(filename=WAVPATH)
NFRAME = int(FILETIME) / DURATION  # allow truncation
DUMPFILE = "data.npy"
FPS = 5


def single_image(argtuple):
    y, i_frame, i_second = argtuple
    fractional_second = float(i_second) / FPS
    abs_index = i_frame * DURATION * FPS + i_second
    time = DURATION*i_frame + fractional_second
    titlestr = "%s - file time %0.2f seconds" % (BASENAME, time)

    # display the spectrogram
    plt.figure(figsize=(18, 8))
    librosa.display.specshow(
        y, x_axis='time', y_axis='mel', sr=SAMPLERATE, hop_length=N_HOP)

    plt.vlines(
        fractional_second, 0, F_MAX,
        linestyles='dashed', colors='w', alpha=0.6)

    plt.title(titlestr)
    plt.savefig(FRAMEROOT + "/%05d.png" % (abs_index))
    plt.tight_layout()
    plt.close()


def main():
    """ main
    """

    pbar = tqdm.tqdm(total=NFRAME)
    pool = mp.Pool(NUMPROC)
    init = False
    if not os.path.exists(FRAMEROOT):
        os.makedirs(FRAMEROOT)

    for i_frame in range(10, NFRAME):
        # load the audio
        x, sr = librosa.core.load(
            WAVPATH, sr=SAMPLERATE,
            offset=DURATION * i_frame, duration=DURATION)

        # compute the spectrogram
        x = librosa.power_to_db(
            librosa.feature.melspectrogram(
                y=x, hop_length=N_HOP, n_fft=N_FFT, sr=SAMPLERATE),
            ref=np.max)

        if not init:
            f_mean = np.sum(x, axis=1)
            init = True
        else:
            f_mean += np.sum(x, axis=1)

        # loop updates
        pbar.update(1)
        pool.map(
            single_image,
            [(x, i_frame, i_second) for i_second in range(FPS*DURATION)])

    np.save(BASENAME + 'f_mean.npy', f_mean)
    pbar.close()

    subprocess.call([
        "ffmpeg", '-r', '5', '-i', FRAMEROOT + '%05d.png', '-i', WAVPATH,
        '-shortest', '-c:v', 'libx264', '-c:a', 'aac', '-strict', '-2',
        '-pix_fmt', 'yuv420p', '-crf', '23', '-r', '5', '-y',
        ROOT + "/videos/" + BASENAME + '.mp4'])


if __name__ == '__main__':
    main()
