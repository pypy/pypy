# NOT_RPYTHON
"""
The 'sys' module.
"""

import sys 

def excepthook(exctype, value, traceback):
    """Handle an exception by displaying it with a traceback on sys.stderr."""
    try:
        from traceback import print_exception
        print_exception(exctype, value, traceback)
    except:
        if not excepthook_failsafe(exctype, value):
            raise

def excepthook_failsafe(exctype, value):
    # This version carefully tries to handle all bad cases (e.g. an
    # ImportError looking for traceback.py), but may still raise.
    # If it does, we get "Error calling sys.excepthook" from app_main.py.
    try:
        # first try to print the exception's class name
        stderr = sys.stderr
        stderr.write(getattr(exctype, '__name__', exctype))
        # then attempt to get the str() of the exception
        try:
            s = str(value)
        except:
            s = '<failure of str() on the exception instance>'
        # then print it, and don't worry too much about the extra space
        # between the exception class and the ':'
        if s:
            stderr.write(': %s\n' % (s,))
        else:
            stderr.write('\n')
        return True     # successfully printed at least the class and value
    except:
        return False    # got an exception again... ignore, report the original

def exit(exitcode=0):
    """Exit the interpreter by raising SystemExit(exitcode).
If the exitcode is omitted or None, it defaults to zero (i.e., success).
If the exitcode is numeric, it will be used as the system exit status.
If it is another kind of object, it will be printed and the system
exit status will be one (i.e., failure)."""
    # note that we cannot use SystemExit(exitcode) here.
    # The comma version leads to an extra de-tupelizing
    # in normalize_exception, which is exactly like CPython's.
    raise SystemExit, exitcode

def exitfunc():
    """Placeholder for sys.exitfunc(), which is called when PyPy exits."""

#import __builtin__

def callstats():
    """Not implemented."""
    return None

copyright_str = """
Copyright 2003-2010 PyPy development team.
All rights reserved.
For further information see http://www.codespeak.net/pypy.

Portions Copyright (c) 2001-2008 Python Software Foundation.
All Rights Reserved.

Portions Copyright (c) 2000 BeOpen.com.
All Rights Reserved.

Portions Copyright (c) 1995-2001 Corporation for National Research Initiatives.
All Rights Reserved.

Portions Copyright (c) 1991-1995 Stichting Mathematisch Centrum, Amsterdam.
All Rights Reserved.
"""
