import py
import os
import time
import autopath
from pypy.rlib.rsdl import RSDL, RMix, RSDL_helper
from pypy.rpython.lltypesystem import lltype, rffi

def test_open_mixer():
    if RMix.OpenAudio(22050, RSDL.AUDIO_S16LSB, 2, 1024) != 0:
        error = rffi.charp2str(RSDL.GetError())
        raise Exception(error)
    RMix.CloseAudio()

def test_load_wav():
    if RMix.OpenAudio(22050, RSDL.AUDIO_S16LSB, 2, 1024) != 0:
        error = rffi.charp2str(RSDL.GetError())
        raise Exception(error)
    filename = rffi.str2charp('applause.wav')
    RMix.LoadWAV(filename)
    rffi.free_charp(filename)
    RMix.CloseAudio()

def test_play_wav():
    if RMix.OpenAudio(22050, RSDL.AUDIO_S16LSB, 2, 1024) != 0:
        error = rffi.charp2str(RSDL.GetError())
        raise Exception(error)
    filename = rffi.str2charp('applause.wav')
    applause = RMix.LoadWAV(filename)
    rffi.free_charp(filename)
    RMix.PlayChannel(-1, applause, -1)
    time.sleep(1)
    RMix.CloseAudio()

