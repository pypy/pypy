# NOT_RPYTHON (no point unless app_sre.py is made RPython too)

# Constants and magic numbers for app_sre.py.
# Moving these values in a separate file allows app_sre.py not to be loaded
# by app-level code that just inspects the _sre magic numbers.

import sys

# Identifying as _sre from Python 2.3 or 2.4
if sys.version_info[:2] >= (2, 4):
    MAGIC = 20031017
else:
    MAGIC = 20030419

# In _sre.c this is bytesize of the code word type of the C implementation.
# There it's 2 for normal Python builds and more for wide unicode builds (large 
# enough to hold a 32-bit UCS-4 encoded character). Since here in pure Python
# we only see re bytecodes as Python longs, we shouldn't have to care about the
# codesize. But sre_compile will compile some stuff differently depending on the
# codesize (e.g., charsets).
if sys.maxunicode == 65535:
    CODESIZE = 2
else:
    CODESIZE = 4

copyright = "_sre.py 2.4a Copyright 2005 by Nik Haldimann"


def getcodesize():
    return CODESIZE
