#!/usr/bin/python  
# encoding:utf-8  
# Filename : processAudio.py  
# author by :morespeech  
# python2.7  
# platform:visual studio code, windows  
# topic: practice every day  
# detial: process audio  

# !/usr/bin/env python  
# -*- coding:utf-8 -*-  

import os
import wave
import pyaudio
import pylab as pl
import numpy as np


class cProcessAudio:
    def __init__(self):
        pass

    # public function
    # read file to buffer
    def readWav(self, filename, mode):
        if not os.path.exists(filename):
            return
        else:
            fileHandle = wave.open(filename, mode)
            params = fileHandle.getparams()
            nchannels, sampwidth, samplerate, nsamples = params[:4]
            # read the data  
            str_data = fileHandle.readframes(nsamples)
            fileHandle.close()

            wave_data = np.fromstring(str_data, dtype=np.short)
            if params[0] == 2:
                wave_data.shape = -1, 2
                wave_data = wave_data.T
            return wave_data

            # write buffer to file, only mono

    def writeWav(self, outfilename, writemode, data, fs, nchannel):
        fileHandle = wave.open(outfilename, writemode)
        fileHandle.setnchannels(nchannel)
        fileHandle.setsampwidth(2)
        fileHandle.setframerate(fs)
        fileHandle.writeframes(data.tostring())
        fileHandle.close()

    # record wav
    def recordWav(self, filename, time, fs, nchannel):
        pa = pyaudio.PyAudio()
        save_buffer = ''
        buffer_size = 1000
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=fs,
            input=True,
            frames_per_buffer=buffer_size)

        read_time_per_second = fs / buffer_size
        cnt = 0
        while cnt < time * read_time_per_second:
            str_data = stream.read(buffer_size)
            save_buffer += str_data
            cnt += 1

        wave_data = np.fromstring(save_buffer, dtype=np.short)
        self.writeWav(filename, "wb", wave_data, fs, nchannel)
        save_buffer = ''

    # play wav
    def playWav(self, filename):
        fileHandle = wave.open(filename, "rb")
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(fileHandle.getsampwidth()),
            channels=fileHandle.getnchannels(),
            rate=fileHandle.getframerate(),
            output=True)
        data = fileHandle.readframes(1024)
        while data != '':
            stream.write(data)
            data = fileHandle.readframes(1024)
        stream.close()
        p.terminate()

    # plot wav
    def plotWav(self, data, fs, nchannel):
        if 2 == nchannel:
            length = len(data[0])
            time = np.arange(0, length) * (1.0 / fs)
            pl.subplot(211)
            pl.plot(time, data[0])
            pl.subplot(212)
            pl.plot(time, data[1], c="g")
            pl.xlabel("time (seconds)")
            pl.show()
        else:
            length = len(data)
            time = np.arange(0, length) * (1.0 / fs)
            pl.plot(time, data)
            pl.show()


            # demo


if __name__ == "__main__":
    data = ''
    data = cProcessAudio().readWav("1.wav", "rb")
    # cProcessAudio().writeWav("new_1.wav", "wb", data, 8000, 1)  
    # cProcessAudio().plotWav(data, 8000, 2)  
    # cProcessAudio().playWav("1.wav")  
    cProcessAudio().recordWav("new_2.wav", 5, 8000, 1)  