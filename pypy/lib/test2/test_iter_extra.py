# -*- coding: iso-8859-1 -*-
import unittest, test.test_support
import pickle

class FakeIterator(object):
    def __init__(self, *a):
        pass
    def __iter__(self):
        return self
    # no next method -- which is why it's *fake*!

# in CPython, behavior of iter(FakeIterator()) differs depending on
# whether class FakeIterator is old-style or new-style.  Currently
# pypy is following the ``old-style'' diagnostic behavior since that
# appears to be necessary to make test_itertools.py work (sigh!!!).
# So we can't sensibly test this, for now, until that issue may be
# better decided in the future -- AM

class IterTest(unittest.TestCase):

    def dont_test_fakeiterator(self):
        x = FakeIterator()
        self.assertRaises(TypeError, iter, x)
        x.next = lambda: 23
        self.assertRaises(TypeError, iter, x)

def test_main():
    test.test_support.run_unittest(IterTest)

if __name__ == "__main__":
    test_main()
