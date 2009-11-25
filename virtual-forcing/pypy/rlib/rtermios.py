# This are here only because it's always better safe than sorry.
# The issue is that from-time-to-time CPython's termios.tcgetattr
# returns list of mostly-strings of length one, but with few ints
# inside, so we make sure it works

import termios
from termios import *

def tcgetattr(fd):
    # NOT_RPYTHON
    lst = list(termios.tcgetattr(fd))
    cc = lst[-1]
    next_cc = []
    for c in cc:
        if isinstance(c, int):
            next_cc.append(chr(c))
        else:
            next_cc.append(c)
    lst[-1] = next_cc
    return tuple(lst)

def tcsetattr(fd, when, mode):
    # NOT_RPYTHON
    # there are some bizarre requirements for that, stealing directly
    # from cpython
    mode_l = list(mode)
    if mode_l[3] & termios.ICANON:
        cc = mode_l[-1]
        cc[termios.VMIN] = ord(cc[termios.VMIN])
        cc[termios.VTIME] = ord(cc[termios.VTIME])
        mode_l[-1] = cc
    return termios.tcsetattr(fd, when, mode_l)
