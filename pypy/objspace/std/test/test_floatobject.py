#!/usr/bin/env python
import unittest
import sys
import os

#Start HACK

#######################################
# Workaround to give the modules 
# an "objectspace"
#######################################

import objspace
thisdir = os.getcwd()
syspath = sys.path
sys.path.insert(0,thisdir)
sys.path.append('..')


#######################################
# import the module you want to test
# import yourmodule
#######################################

os.chdir('..')
import floatobject as fl
os.chdir(thisdir)

# End HACK

True,False = (1==1),(1==0)

class TestW_FloatObject(unittest.TestCase):

    def setUp(self):
        self.space = objspace.StdObjSpace

    def tearDown(self):
        pass

    def test_float(self):
        f1 = fl.W_FloatObject(1.0)
        result = fl.float_float(self.space,f1)
        assert result == f1

    def test_repr(self):
        x = 1.0
        f1 = fl.W_FloatObject(x)
        result = fl.float_repr(self.space,f1)
        assert self.space.unwrap(result) == repr(x)

    def test_str(self):
        x = 1.0
        f1 = fl.W_FloatObject(x)
        result = fl.float_str(self.space,f1)
        assert self.space.unwrap(result) == str(x)

    def test_hash(self):
        x = 1.0
        f1 = fl.W_FloatObject(x)
        result = fl.float_hash(self.space,f1)
        assert self.space.unwrap(result) == hash(x)

    def test_add(self):
        f1 = fl.W_FloatObject(1.0)
        f2 = fl.W_FloatObject(2.0)
        result = fl.float_float_add(self.space,f1,f2)
        assert result.floatval == 3.0

    def test_sub(self):
        f1 = fl.W_FloatObject(1.0)
        f2 = fl.W_FloatObject(2.0)
        result = fl.float_float_sub(self.space,f1,f2)
        assert result.floatval == -1.0

    def test_mul(self):
        f1 = fl.W_FloatObject(1.0)
        f2 = fl.W_FloatObject(2.0)
        result = fl.float_float_mul(self.space,f1,f2)
        assert result.floatval == 2.0

    def test_div(self):
        f1 = fl.W_FloatObject(1.0)
        f2 = fl.W_FloatObject(2.0)
        result = fl.float_float_div(self.space,f1,f2)
        assert result.floatval == 0.5

    def test_mod(self):
        x = 1.0
        y = 2.0
        f1 = fl.W_FloatObject(x)
        f2 = fl.W_FloatObject(y)
        v = fl.float_float_mod(self.space,f1,f2)
        assert v.floatval == x % y

    def test_divmod(self):
        x = 1.0
        y = 2.0
        f1 = fl.W_FloatObject(x)
        f2 = fl.W_FloatObject(y)
        wrappedTuple = fl.float_float_divmod(self.space,f1,f2)
        v,w = self.space.unwrap(wrappedTuple)
        assert (v.floatval,w.floatval) == divmod(x,y)

    def test_pow(self):
        x = 1.0
        y = 2.0
        f1 = fl.W_FloatObject(x)
        f2 = fl.W_FloatObject(y)
        v = fl.float_float_pow(self.space,f1,f2)
        assert v.floatval == x ** y


if __name__ == '__main__':
    unittest.main()
