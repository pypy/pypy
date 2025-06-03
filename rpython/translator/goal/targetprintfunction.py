from __future__ import print_function

# __________  Entry point  __________

def entry_point(argv):
    if len(argv) > 1:
        name = argv[1]
    else:
        name = "print-function"

    print("Hello,", name + "!")

    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point
