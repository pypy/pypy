import imp
import os
import sys
import unittest

PATH = None
EXT = None
FILENAME = None
NAME = '_testcapi'
_file_exts = [x[0] for x in imp.get_suffixes() if x[2] == imp.C_EXTENSION]
try:
    for PATH in sys.path:
        for EXT in _file_exts:
            FILENAME = NAME + EXT
            FILEPATH = os.path.join(PATH, FILENAME)
            if os.path.exists(os.path.join(PATH, FILENAME)):
                raise StopIteration
    else:
        # Try a direct import
        try:
            import _testcapi
        except ImportError:
            PATH = EXT = FILENAME = FILEPATH = None
        else:
            FILEPATH = _testcapi.__file__
            PATH, FILENAME = os.path.split(FILEPATH)
            _, EXT = os.path.splitext(FILEPATH)
except StopIteration:
    pass
del _file_exts


def skip_unless__testcapi(func):
    msg = "Requires the CPython C Extension API ({!r} module)".format(NAME)
    return unittest.skipUnless(PATH, msg)(func)
