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
import unittest
import autopath

from pypy.appspace import cmathmodule
from pypy.appspace.test.test_complexobject import equal

def enumerate():
    valueRange = [-12.34, -3, -1, -0.5, 0, 0.5, 1, 3, 12.34]
    res = []
    for x0 in valueRange:
        for y0 in valueRange:
            z = complex(x0,y0)
            res.append(z)
    return res



class TestCMathModule: 

    def assertAEqual(self, a, b):
        if not equal(a, b):
            raise self.failureException, '%s ~== %s'%(a, b)

    def test_funcs(self):
        "Compare many functions with CPython."
        
        for z in enumerate():

            for op in "sqrt acos acosh asin asinh atan atanh cos cosh exp".split():
                if op == "atan" and equal(z, complex(0,-1)) or equal(z, complex(0,1)):
                    continue
                if op == "atanh" and equal(z, complex(-1,0)) or equal(z, complex(1,0)):
                    continue
                op0 = cmath.__dict__[op](z)
                op1 = cmathmodule.__dict__[op](z)
                self.assertAEqual(op0, op1)


    def test_log_log10(self):
        "Compare log/log10 functions with CPython."
        
        for z in enumerate():
            for op in "log log10".split():
                if z != 0:
                    op0 = cmath.__dict__[op](z)
                    op1 = cmathmodule.__dict__[op](z)
                    self.assertAEqual(op0, op1)

