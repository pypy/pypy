import sys, os
import unittest

testdir   = os.path.dirname(os.path.abspath(__file__))
parentdir = os.path.dirname(testdir)
rootdir   = os.path.dirname(os.path.dirname(parentdir))

sys.path.insert(0, os.path.dirname(rootdir))

class TestCase_w(unittest.TestCase):
    """ enrich TestCase with wrapped-methods """

    def failUnless_w(self, condition_w, msg=None):
        condition = self.space.is_true(condition_w)
        return self.failUnless(condition, msg)

    def failIf_w(self, condition_w, msg=None):
        condition = self.space.is_true(condition_w)
        return self.failIf(condition, msg)

    def assertEqual_w(self, first_w, second_w, msg=None):
        condition_w = self.space.eq(first_w, second_w)
        condition = self.space.is_true(condition_w)
        return self.failUnless(condition, msg)

    def assertNotEqual_w(self, first_w, second_w, msg=None):
        condition_w = self.space.eq(first_w, second_w)
        condition = self.space.is_true(condition_w)
        return self.failIf(condition, msg)

