"""
The 'sys' module.
"""

import sys 

# XXX not called by the core yet
def excepthook(exctype, value, traceback):
    from traceback import print_exception
    print_exception(exctype, value, traceback)

__excepthook__ = excepthook  # this is exactly like in CPython

def exit(exitcode=0):
    # note that we cannot use SystemExit(exitcode) here.
    # The comma version leads to an extra de-tupelizing
    # in normalize_exception, which is exactly like CPython's.
    raise SystemExit, exitcode

#import __builtin__

def getfilesystemencoding():
    """ getfilesystemencoding() -> string
        Return the encoding used to convert Unicode filenames in
        operating system filenames.
    """
    if sys.platform == "win32":
        encoding = "mbcs"
    elif sys.platform == "darwin":
        encoding = "utf-8"
    else:
        encoding = None
    return encoding
