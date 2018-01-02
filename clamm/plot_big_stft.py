"""
Convert a large audio wav file (album length, i.e. > 30 minutes typically)
into a series of videos consisting of the audio synchronized with images of the
spectrogram.
"""
import os
import sys
import glob

import tqdm
import numpy as np
import librosa.core
import librosa.display
import matplotlib
import matplotlib.pyplot as plt

SAMPLERATE = 44.1e3     # samples/sec
WAVPATH = sys.argv[1]


def image_to_cursor_frames(ax, x, duration, savebase):
    """ image_to_cursor_frames
    """
    frame_root = "frames"
    if not os.path.exists(frame_root):
        os.mkdir(frame_root)
    [os.remove(p) for p in glob.glob(frame_root + "/*.png")]

    fft_freqs = librosa.fft_frequencies(sr=SAMPLERATE)
    f_max = np.max(fft_freqs)

    with tqdm.tqdm(total=duration) as pbar:
        for i_second in range(duration):
            pbar.update(1)
            lcs = [child
                   for child in ax.get_children()
                   if isinstance(child, matplotlib.collections.LineCollection)]
            [lc.remove() for lc in lcs]

            plt.vlines(
                i_second, 0, f_max,
                linestyles='dashed',
                colors='w', alpha=0.8)
            plt.savefig(
                os.path.join(
                    frame_root,
                    savepath(savebase, ('frame', i_second))))


def savepath(base, appendages, ext=".png"):
    """ savepath
    """
    basestr = "%s" % (
        os.path.splitext(os.path.basename(base))[0].replace(" ", "_").lower())
    basestr += "-%s%0.4d" % (appendages[0], appendages[1])
    return basestr + ext


def main():
    """ main
    """
    file_time = librosa.core.get_duration(filename=WAVPATH)

    time_remain = file_time
    duration = 90  #
    n_fft = 2048
    hop_length = int(3.0 / 4 * n_fft)

    pbar = tqdm.tqdm(total=file_time)
    while time_remain > 0:
        # loop updates
        pbar.update(duration)
        duration = duration if time_remain > duration else time_remain

        # load the audio
        x, sr = librosa.core.load(
            WAVPATH, sr=SAMPLERATE,
            offset=file_time - time_remain, duration=duration)
        time_remain -= duration

        # compute the spectrogram
        x = librosa.stft(
            x, hop_length=hop_length, n_fft=n_fft, win_length=n_fft)

        # display the spectrogram
        plt.figure(figsize=(16, 6))
        spec = librosa.display.specshow(
            librosa.amplitude_to_db(x, ref=np.max),
            x_axis='time', y_axis='log', sr=sr, hop_length=hop_length)
        plt.tight_layout()

        # save at static image of result
        savename = savepath(
            WAVPATH, ("offset", file_time - time_remain - duration))
        plt.title(savename.replace(".png", ""))
        plt.savefig(savename)

        image_to_cursor_frames(spec, x, duration, savename)

        plt.close()
    pbar.close()


if __name__ == '__main__':
    main()
