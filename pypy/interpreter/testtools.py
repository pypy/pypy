import os
import unittest

def get_tests_for_dir(directory):
    files = os.listdir(directory)
    testfiles = [f[:-3] for f in files if f.startswith('test_') and f.endswith('.py')]

    ts = unittest.TestSuite()

    tl = unittest.TestLoader()
    
    for testfile in testfiles:
        mod = __import__(testfile)
        ts.addTest(tl.loadTestsFromModule(mod))

    return ts
    
    
