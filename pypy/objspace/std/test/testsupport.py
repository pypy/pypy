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

import pypy.interpreter.unittest_w
TestCase = pypy.interpreter.unittest_w.TestCase_w
import unittest
main = unittest.main

objspace_path = os.environ.get('OBJSPACE')
if not objspace_path or '.' not in objspace_path:
    import pypy.objspace.trivial
    objspace = pypy.objspace.trivial.TrivialObjSpace
else:
    objspace_pieces = objspace_path.split('.')
    objspace_path = '.'.join(objspace_pieces[:-1])
    objspace_module = __import__(objspace_path)
    for piece in objspace_pieces[1:-1]:
        objspace_module = getattr(objspace_module, piece)
    objspace_classname = objspace_pieces[-1]
    objspace = getattr(objspace_module, objspace_classname)

