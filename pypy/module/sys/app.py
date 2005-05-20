# NOT_RPYTHON   -- flowing results in
# AttributeError:   << 'FlowObjSpace' object has no attribute 'w_AttributeError'
# XXX investigate!
"""
The 'sys' module.
"""

import sys 

def excepthook(exctype, value, traceback):
    from traceback import print_exception
    print_exception(exctype, value, traceback)

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

def callstats():
    """callstats() -> tuple of integers

Return a tuple of function call statistics, if CALL_PROFILE was defined
when Python was built.  Otherwise, return None.

When enabled, this function returns detailed, implementation-specific
details about the number of function calls executed. The return value is
a 11-tuple where the entries in the tuple are counts of:
0. all function calls
1. calls to PyFunction_Type objects
2. PyFunction calls that do not create an argument tuple
3. PyFunction calls that do not create an argument tuple
   and bypass PyEval_EvalCodeEx()
4. PyMethod calls
5. PyMethod calls on bound methods
6. PyType calls
7. PyCFunction calls
8. generator calls
9. All other calls
10. Number of stack pops performed by call_function()"""
    return None
