import os
import unittest

def get_tests_for_dir(directory):
    files = os.listdir(directory)
    testfiles = [f[:-3] for f in files
                 if f.startswith('test_') and f.endswith('.py')]

    ts = unittest.TestSuite()

    tl = unittest.TestLoader()
    
    for testfile in testfiles:
        mod = __import__(testfile)
        ts.addTest(tl.loadTestsFromModule(mod))

    return ts

def objspace():
    objspace_path = os.environ.get('OBJSPACE')
    if not objspace_path or '.' not in objspace_path:
        return trivobjspace()
    else:
        return stdobjspace()

_trivobjspace = None

def trivobjspace():
    global _trivobjspace
    if _trivobjspace:
        return _trivobjspace
    from pypy.objspace.trivial import TrivialObjSpace
    _trivobjspace = TrivialObjSpace()
    return _trivobjspace

_stdobjspace = None

def stdobjspace():
    global _stdobjspace
    if _stdobjspace:
        return _stdobjspace
    from pypy.objspace.std import StdObjSpace
    _stdobjspace = StdObjSpace()
    return _stdobjspace
