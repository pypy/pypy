#!/usr/bin/env pypy
# encoding: utf-8
from __future__ import unicode_literals
import pyrepl.readline
while True:
    try:
        print(raw_input("\x1b[1;31m？>\x1b[0m ".encode("utf-8")))
    except EOFError:
        break
