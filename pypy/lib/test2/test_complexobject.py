#!/usr/bin/env python

"""

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

Note that this test currently runs at cpython-level and not
at any application level .... 

"""
#taken from CPython 2.3 (?)

"""
Test module for class complex in complexobject.py

As it seems there are some numerical differences in 
the __div__ and __divmod__ methods which have to be 
sorted out.
"""

import autopath

import math
import cmath
import sys
import types
#import unittest

#from pypy.tool import testit
#from pypy.appspace.complexobject import complex as pycomplex

#from pypy.module.test.applevel_in_cpython import applevel_in_cpython
#our_own_builtin = applevel_in_cpython('__builtin__')
#pycomplex = our_own_builtin.complex
    
from pypy.module.builtin.app_complex import complex as pycomplex

try:
    unicode
    have_unicode = 0 # pypy doesn't have unicode, we know it ...
except NameError:
    have_unicode = 0


def equal(a, b):
    "Compare two complex or normal numbers. 0 if different, 1 if roughly equal."
    
    numTypes = [types.IntType, types.LongType, types.FloatType]
    da, db = dir(a), dir(b)
    
    if 'real' in da and 'real' in db and 'imag' in da and 'imag' in db:
        if math.fabs(a.real-b.real) > 1e-10:
            return 0
        if math.fabs(a.imag-b.imag) > 1e-10:
            return 0
        else:
            return 1
    elif type(a) in numTypes and type(b) in numTypes:
        if math.fabs(a-b) > 1e-10:
            return 0
        else:
            return 1
    



def enumerate():
    valueRange = [-3, -0.5, 0, 1]
    res = []
    for x0 in valueRange:
        for y0 in valueRange:
            for x1 in valueRange:
                for y1 in valueRange:
                    z0c = complex(x0,y0)
                    z1c = complex(x1,y1)
                    z0p = pycomplex(x0,y0)
                    z1p = pycomplex(x1,y1)
                    res.append((z0c, z1c, z0p, z1p))

    return res



class TestComplex:

    def assertAEqual(self, a, b):
        assert equal(a, b)

    def test_wrongInit1(self):
        "Compare wrong init. with CPython."
        
        try:
            complex("1", "1")
        except TypeError:
            pass
        else:
            self.fail('complex("1", "1")')

        try:
            pycomplex("1", "1")
        except TypeError:
            pass
        else:
            self.fail('complex("1", "1")')


    def test_wrongInit2(self):
        "Compare wrong init. with CPython."
        
        try:
            complex(1, "1")
        except TypeError:
            pass
        else:
            self.fail('complex(1, "1")')

        try:
            pycomplex(1, "1")
        except TypeError:
            pass
        else:
            self.fail('complex(1, "1")')


    def test_wrongInitFromString(self):
        "Compare string init. with CPython."

        if complex("  3.14+J  ") != 3.14+1j:
            self.fail('complex("  3.14+J  )"')
        if not equal(pycomplex("  3.14+J  "), pycomplex(3.14,1)):
            self.fail('complex("  3.14+J  )"')


    def test_wrongInitFromUnicodeString(self):
        "Compare unicode string init. with CPython."

        if have_unicode:
            if complex(unicode("  3.14+J  ")) != 3.14+1j:
                self.fail('complex(u"  3.14+J  )"')
            if not equal(pycomplex(unicode("  3.14+J  ")), pycomplex(3.14, 1)):
                self.fail('complex(u"  3.14+J  )"')


    def test_class(self):
        "Compare class with CPython."
        
        class Z:
            def __complex__(self):
                return 3.14j
        z = Z()
        if complex(z) != 3.14j:
            self.fail('complex(classinstance)')

        if not equal(complex(z), pycomplex(0, 3.14)): 
            self.fail('complex(classinstance)')


    def test_add_sub_mul_div(self):
        "Compare add/sub/mul/div with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            mc = z0c*z1c
            mp = z0p*z1p
            self.assertAEqual(mc, mp)

            sc = z0c+z1c
            sp = z0p+z1p
            self.assertAEqual(sc, sp)

            dc = z0c-z1c
            dp = z0p-z1p
            self.assertAEqual(dc, dp)

            if not equal(z1c, complex(0,0)): 
                qc = z0c/z1c
                qp = z0p/z1p
                self.assertAEqual(qc, qp)

                
    def test_special(self):
        "Compare special methods with CPython."
        
        for (x, y) in [(0,0), (0,1), (1,3.)]:
            zc = complex(x, y)
            zp = pycomplex(x, y)

            self.assertAEqual(zc, zp)
            self.assertAEqual(-zc, -zp)
            self.assertAEqual(+zc, +zp)
            self.assertAEqual(abs(zc), abs(zp))
            self.assertAEqual(zc, zp)
            #self.assertEqual(zc.conjugate(), zp.conjugate()) XXX 
            assert str(zc) == str(zp)
            assert hash(zc) == hash(zp)


    # this fails on python2.3 and is depreacted anyway
    def _test_divmod(self):
        "Compare divmod with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            mc = z0c*z1c
            mp = z0p*z1p
            self.assertAEqual(mc, mp)

            if not equal(z1c, complex(0,0)): 
                ddc, mmc = divmod(z0c, z1c)
                self.assertAEqual(ddc*z1c + mmc, z0c)
                ddp, mmp = divmod(z0p, z1p)
                self.assertAEqual(ddp*z1p + mmp, z0p)
                self.assertAEqual(ddc, ddp)
                self.assertAEqual(mmc, mmp)


    # these fail on python2.3
    def _test_mod(self):
        "Compare mod with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            mc = z0c*z1c
            mp = z0p*z1p
            self.assertAEqual(mc, mp)

            if not equal(z1c, complex(0,0)): 
                rc = z0c%z1c
                rp = z0p%z1p
                self.assertAEqual(rc, rp)
                    
    def test_div(self):
        "Compare mod with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            mc = z0c*z1c
            mp = z0p*z1p
            self.assertAEqual(mc, mp)

            if not equal(z1c, complex(0,0)): 
                rc = z0c/z1c
                rp = z0p/z1p
                self.assertAEqual(rc, rp)
                    

    def test_pow(self):
        "Compare pow with CPython."
        
        for (z0c, z1c, z0p, z1p) in enumerate():
            if not equal(z0c, 0j) and (z1c.imag != 0.0):
                pc = z0c**z1c
                pp = z0p**z1p
                self.assertAEqual(pc, pp)
                pc = z0c**z0c.real
                pp = z0p**z0p.real
                self.assertAEqual(pc, pp)
                
    def test_complex(self):                
        "Compare complex() with CPython (with complex arguments)"
        ours = pycomplex(pycomplex(1,10), 100)
        cpy = complex(complex(1,10), 100)
        self.assertAEqual(ours, cpy)

        ours = pycomplex(pycomplex(1,10), pycomplex(100,1000))
        cpy = complex(complex(1,10), complex(100,1000))
        self.assertAEqual(ours, cpy)

        ours = pycomplex(10, pycomplex(100,1000))
        cpy = complex(10, complex(100,1000))
        self.assertAEqual(ours, cpy)
