#!/usr/bin/env python


"""
Test module for functions in stringmodule.py

"""

import string as c_py_string
import unittest

import autopath
from pypy.tool import test
from pypy.appspace import string as pypy_string

class TestStringmodule(unittest.TestCase):
    def regression(self, sFuncname, *args, **kwargs):
        try:
            c_py_res = getattr(c_py_string, sFuncname)(*args, **kwargs)
        except Exception, ce:
            c_py_res = ce.__class__
        
        try:
            pypy_res = getattr(pypy_string, sFuncname)(*args, **kwargs)
        except Exception, pe:
            pypy_res = pe.__class__
        
        self.assertEqual(c_py_res, pypy_res, 'not equal \n1:<%s>\n2:<%s>' % (c_py_res, pypy_res))


    def test_maketrans(self):
        self.regression('maketrans','','')
        self.regression('maketrans','a','b')
        self.regression('maketrans','aa','bb')
        self.regression('maketrans','aa','')


if __name__ == "__main__":
    test.main()