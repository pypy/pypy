# -*- coding: iso-8859-1 -*-
import unittest, test.test_support
import sys, cStringIO

class ObjectTest(unittest.TestCase):

    def test_hash_builtin(self):
        o = object()
        self.assertEquals(hash(o), id(o))

    def test_hash_method(self):
        o = object()
        self.assertEquals(hash(o), o.__hash__())

    def test_hash_list(self):
        l = range(5)
        self.assertRaises(TypeError, hash, l)

def test_main():
    test.test_support.run_unittest(ObjectTest)

if __name__ == "__main__":
    test_main()
