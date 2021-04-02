#!/usr/bin/env pypy3
import pyrepl.readline
while True:
    try:
        print(input("\x1b[1;31m？>\x1b[0m "))
    except EOFError:
        break
