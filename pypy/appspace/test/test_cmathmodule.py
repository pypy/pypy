#!/usr/bin/env python

# taken from CPython 2.3

"""
Test module for functions in cmathmodule.py

It seems the log and log10 functions are generating errors
due to numerical problems with floor() in complex.__div__.
"""

import math
import cmath
import sys
import types
import unittest
import testsupport

try:
    from pypy.appspace import cmathmodule
    from pypy.appspace.complexobject import complex as pycomplex
except ImportError:
    import cmathmodule
    from complexobject import complex as pycomplex

from test_complexobject import equal, enumerate


class TestCMathModule(unittest.TestCase):

    def test_funcs(self):
        "Compare many functions with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            mc = z0c*z1c
            mp = z0p*z1p
            self.assert_(equal(mc, mp))

            for op in "sqrt acos acosh asin asinh atan atanh cos cosh exp".split():
                if op == "atan" and equal(z0c, complex(0,-1)) or equal(z0c, complex(0,1)):
                    continue
                if op == "atanh" and equal(z0c, complex(-1,0)) or equal(z0c, complex(1,0)):
                    continue
                op0 = cmath.__dict__[op](z0c)
                op1 = cmathmodule.__dict__[op](z0p)
                self.assert_(equal(op0, op1))

            # check divisions
            if equal(z0c, complex(0,0)) or equal(z1c, complex(0,0)):
                continue
            self.assert_(equal(mc/z0c, mp/z0p))
            self.assert_(equal(mc/z1c, mp/z1p))


    def test_log_log10(self):
        "Compare log/log10 functions with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            for op in "log log10".split():
                op0 = cmath.__dict__[op](z0c)
                op1 = cmathmodule.__dict__[op](z0p)
                self.assert_(equal(op0, op1))



if __name__ == "__main__":
    unittest.main()
