import sys
from pypy.rlib.rarithmetic import ovfcheck

class BaseTestOverflow:

    def check(self, fn, args, expected=None):
        res1 = self.interpret(fn, args)
        if expected is not None:
            res2 = expected
        else:
            res2 = fn(*args)
        assert res1 == res2

    def test_add(self):
        def fn(x, y):
            try:
                return ovfcheck(x+y)
            except OverflowError:
                return 42
        self.check(fn, [sys.maxint, 1])

    def test_add2(self):
        def fn(x):
            try:
                return ovfcheck(x+1)   # special 'int_add_nonneg_ovf' operation
            except OverflowError:
                return 42
        self.check(fn, [sys.maxint])

    def test_sub(self):
        def fn(x, y):
            try:
                return ovfcheck(x-y)
            except OverflowError:
                return 42
        self.check(fn, [-sys.maxint, 2])

    def test_mul(self):
        def fn(x, y):
            try:
                return ovfcheck(x*y)
            except OverflowError:
                return 42
        self.check(fn, [sys.maxint/2 + 1, 2])

    def test_lshift(self):
        def fn(x, y):
            try:
                return ovfcheck(x<<y)
            except OverflowError:
                return 42
        self.check(fn, [2, 30])


    def test_neg(self):
        def fn(x):
            try:
                return ovfcheck(-x)
            except OverflowError:
                return 42
        self.check(fn, [-sys.maxint-1])

    def test_mod(self):
        def fn(x, y):
            try:
                return ovfcheck(x % y)
            except OverflowError:
                return 42
        # force the expected result to be 42, because direct run of ovfcheck()
        # cannot detect this particular overflow case
        self.check(fn, [-sys.maxint-1, -1], expected=42)

    def test_div(self):
        def fn(x, y):
            try:
                return ovfcheck(x / y)
            except OverflowError:
                return 42
        self.check(fn, [-sys.maxint-1, -1])
