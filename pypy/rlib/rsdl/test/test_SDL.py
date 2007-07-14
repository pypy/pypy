#!/usr/bin/env python

from time import time, sleep
from ctypes import byref

import py.test
py.test.skip("does not work..")
from pypy.rlib.rsdl import SDL
from pypy.translator.c.test.test_genc import compile

def demo():

    if SDL.Init(SDL.INIT_VIDEO) < 0:
        assert 0

    width, height = 640, 480

    screen = SDL.SetVideoMode(width, height, 32, SDL.HWSURFACE)
    assert screen

    frame = 0

    event = SDL.Event()

    running = True
    while running:

        while SDL.PollEvent(byref(event)):
            tp = event.type
    
            if tp == SDL.KEYUP:
                sym = event.key.keysym.sym
                if sym == SDL.K_q:
                    running = False;break
            elif tp == SDL.QUIT:
                running = False;break

        sleep(0.1)

        frame += 1


    SDL.Quit()

    return 0

def test_run():
    demo()

def test_compile():
    _demo = compile(demo, [])
    _demo()




