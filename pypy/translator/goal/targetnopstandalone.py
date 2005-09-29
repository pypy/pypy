import os, sys

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')

# __________  Entry point  __________

def entry_point(argv):
    debug("done!")
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

