"""
Master version of testsupport.py: copy into any subdirectory of pypy
from which scripts need to be run (typically all of the 'test' subdirs)
so that any test can "import testsupport" to ensure the parent of pypy
is on the sys.path -- so that "import pypy.etc.etc." always works.
"""
import sys, os

head = this_path = os.path.abspath(__file__)
while 1:
    head, tail = os.path.split(head)
    if not tail:
        raise EnvironmentError, "pypy not among parents of %r!" % this_path
    elif tail.lower()=='pypy':
        sys.path.insert(0, head)
        break

