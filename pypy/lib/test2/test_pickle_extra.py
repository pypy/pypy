# -*- coding: iso-8859-1 -*-
import unittest, test.test_support
import pickle

class Picklable(object):
    def __init__(self, a=555):
        self.a = a
    def __eq__(self, other):
        return self.a == other.a
    def __str__(self):
        return '%s(%r)' % (self.__class__.__name__, self.a)
    __repr__ = __str__

class PicklableSpecial2(Picklable):
    def __reduce__(self):
        return self.__class__, (self.a,)

class PicklableSpecial3(Picklable):
    def __reduce__(self):
        return self.__class__, (), self.a
    def __setstate__(self, a):
        self.a = a

class PicklableSpecial4(Picklable):
    def __reduce_ex__(self, proto):
        return self.__class__, (), self.a
    def __setstate__(self, a):
        self.a = a

class PickleTest(unittest.TestCase):

    def _pickle_some(self, x):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            s = pickle.dumps(x, proto)
            y = pickle.loads(s)
            self.assertEqual(x, y)

    def test_pickle_plain(self):
        self._pickle_some(Picklable(5))

    def test_pickle_special2(self):
        self._pickle_some(PicklableSpecial2(66))

    def test_pickle_special3(self):
        self._pickle_some(PicklableSpecial3(7))

    def test_pickle_special4(self):
        self._pickle_some(PicklableSpecial4(17))

def test_main():
    test.test_support.run_unittest(PickleTest)

if __name__ == "__main__":
    test_main()
