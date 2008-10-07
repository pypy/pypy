#!/usr/bin/env python
# UserString is a wrapper around the native builtin string type.
# UserString instances should behave similar to builtin string objects.

import unittest
from test import test_support, string_tests

from UserString import UserString, MutableString

class UserStringTest(
    string_tests.CommonTest,
    string_tests.MixinStrUnicodeUserStringTest,
    string_tests.MixinStrStringUserStringTest,
    string_tests.MixinStrUserStringTest
    ):

    type2test = UserString

    fixargs = lambda self, args: args
    subclasscheck = False

class MutableStringTest(UserStringTest):
    type2test = MutableString

    # MutableStrings can be hashed => deactivate test
    def test_hash(self):
        pass

    def test_setitem(self):
        s = self.type2test("foo")
        self.assertRaises(IndexError, s.__setitem__, -4, "bar")
        self.assertRaises(IndexError, s.__setitem__, 3, "bar")
        s[-1] = "bar"
        self.assertEqual(s, "fobar")
        s[0] = "bar"
        self.assertEqual(s, "barobar")

    def test_delitem(self):
        s = self.type2test("foo")
        self.assertRaises(IndexError, s.__delitem__, -4)
        self.assertRaises(IndexError, s.__delitem__, 3)
        del s[-1]
        self.assertEqual(s, "fo")
        del s[0]
        self.assertEqual(s, "o")
        del s[0]
        self.assertEqual(s, "")

    def test_setslice(self):
        s = self.type2test("foo")
        s[:] = "bar"
        self.assertEqual(s, "bar")
        s[1:2] = "foo"
        self.assertEqual(s, "bfoor")
        s[1:-1] = UserString("a")
        self.assertEqual(s, "bar")
        s[0:10] = 42
        self.assertEqual(s, "42")

    def test_delslice(self):
        s = self.type2test("foobar")
        del s[3:10]
        self.assertEqual(s, "foo")
        del s[-1:10]
        self.assertEqual(s, "fo")

    def test_immutable(self):
        s = self.type2test("foobar")
        s2 = s.immutable()
        self.assertEqual(s, s2)
        self.assert_(isinstance(s2, UserString))

    def test_iadd(self):
        s = self.type2test("foo")
        s += "bar"
        self.assertEqual(s, "foobar")
        s += UserString("baz")
        self.assertEqual(s, "foobarbaz")
        s += 42
        self.assertEqual(s, "foobarbaz42")

    def test_imul(self):
        s = self.type2test("foo")
        s *= 1
        self.assertEqual(s, "foo")
        s *= 2
        self.assertEqual(s, "foofoo")
        s *= -1
        self.assertEqual(s, "")

def test_main():
    test_support.run_unittest(UserStringTest, MutableStringTest)

if __name__ == "__main__":
    test_main()
