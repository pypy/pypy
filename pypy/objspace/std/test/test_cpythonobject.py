import unittest, sys, array
import autopath
from pypy.tool import test
from pypy.objspace.std import cpythonobject
from pypy.objspace.std.objspace import OperationError


class TestW_CPythonObject(test.TestCase):

    def setUp(self):
        self.space = test.objspace('std')
        # arbitrary always-wrapped object
        self.stuff = array.array('b', [5,-2,77])

    def tearDown(self):
        pass

    def test_unary(self):
        w1 = self.space.wrap(self.stuff)
        for op, expected in [
            ('id',     id(self.stuff)),
            ('type',   array.ArrayType),
            ('len',    3),
            ('repr',   "array('b', [5, -2, 77])"),
            ('str',    "array('b', [5, -2, 77])"),
            ]:
            w_result = getattr(self.space, op)(w1)
            self.assertEquals(self.space.unwrap(w_result), expected)

    def test_binary(self):
        w1 = self.space.wrap(self.stuff)
        for op, w_arg, expected in [
            ('getattr',   self.space.wrap('count'),      self.stuff.count),
            ('getitem',   self.space.wrap(1),            -2),
            ('getitem',   self.space.wrap(slice(1,2)),   array.array('b', [-2])),
            ]:
            w_result = getattr(self.space, op)(w1, w_arg)
            self.assertEquals(self.space.unwrap(w_result), expected)

    def test_unaryop(self):
        w1 = self.space.wrap(3+4j)
        for op, expected in [
            ('pos',       3+4j),
            ('neg',      -3-4j),
            ('not_',     False),
            ('abs',      5.0),
            ('hash',     hash(3+4j)),
            ]:
            w_result = getattr(self.space, op)(w1)
            self.assertEquals(self.space.unwrap(w_result), expected)

    def test_binaryop(self):
        w1 = self.space.wrap(3+4j)
        w2 = self.space.wrap(1-2j)
        for op, expected in [
            ('add',      (3+4j) + (1-2j)),
            ('sub',      (3+4j) - (1-2j)),
            ('mul',      (3+4j) * (1-2j)),
            ('div',      (3+4j) / (1-2j)),
            ('eq',       False),
            ('ne',       True),
            ]:
            w_result = getattr(self.space, op)(w1, w2)
            self.assertEquals(self.space.unwrap(w_result), expected)

    def test_hash(self):
        # i don't understand this test -- mwh
        w1 = self.space.wrap(self.stuff)
        try:
            self.space.hash(w1)
        except OperationError, e:
            self.assertEquals(e.w_type.cpyobj, TypeError)

    def test_call(self):
        w1 = self.space.wrap(len)
        w_result = self.space.call(w1, self.space.wrap(("hello world",)),
                                       self.space.wrap({}))
        self.assertEquals(self.space.unwrap(w_result), 11)

if __name__ == '__main__':
    test.main()
