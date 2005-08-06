#!/usr/bin/env python
# UserString is a wrapper around the native builtin string type.
# UserString instances should behave similar to builtin string objects.

import unittest
from test import test_support, string_tests

from UserString import UserString

class UserStringTest(
    string_tests.CommonTest,
    string_tests.MixinStrUnicodeUserStringTest,
    string_tests.MixinStrStringUserStringTest,
    string_tests.MixinStrUserStringTest
    ):

    type2test = UserString

    fixargs = lambda self, args: args
    subclasscheck = False

def test_main():
    test_support.run_unittest(UserStringTest)

if __name__ == "__main__":
    test_main()
