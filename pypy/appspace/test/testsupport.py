"""
Master version of testsupport.py: copy into any subdirectory of pypy
from which scripts need to be run (typically all of the 'test' subdirs)
so that any test can "import testsupport" to ensure the parent of pypy
is on the sys.path -- so that "import pypy.etc.etc." always works.

Also, this module exposes a member 'TestCase' that is unittest.TestCase
or a subclass thereof supplying extra methods; and a function 'main'
that is unittest.main or the equivalent.

Furthermore, this module now exposes a member 'objspace' which is
by default class pypy.objspace.trivial.TrivialObjSpace but can be
set to use another objectspace instead; this allows tests to run
under different objectspaces without needing to edit their sources.

For this setting, use environment variable OBJSPACE and set it to
a value such as 'pypy.objspace.trivial.TrivialObjSpace' (which is
also the default if the environment variable is not found or empty
or without any dot in it).

When run as a script, runs all tests found in files called 'test_*.py'
in the same directory.
"""
import sys
import os
import unittest

try:
    head = this_path = os.path.abspath(__file__)
except NameError:
    p = os.path.dirname(sys.argv[0])
    if not p:
        p = os.curdir
    head = this_path = os.path.abspath(p)
while 1:
    head, tail = os.path.split(head)
    if not tail:
        raise EnvironmentError, "pypy not among parents of %r!" % this_path
    elif tail.lower()=='pypy':
        sys.path.insert(0, head)
        break

import pypy.interpreter.unittest_w
from pypy.interpreter.testtools import *

TestCase = pypy.interpreter.unittest_w.IntTestCase
AppTestCase = pypy.interpreter.unittest_w.AppTestCase
main = unittest.main

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(get_tests_for_dir(this_path))
