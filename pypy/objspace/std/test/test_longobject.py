import autopath
import sys
from random import random, randint
from pypy.objspace.std import longobject as lobj
from pypy.objspace.std.objspace import FailedToImplement

objspacename = 'std'

class TestW_LongObject:

    def test_add(self):
        x = 123456789123456789000000L
        y = 123858582373821923936744221L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = lobj.W_LongObject(self.space, *lobj.args_from_long(x * i))
                f2 = lobj.W_LongObject(self.space, *lobj.args_from_long(y * j))
                result = lobj.add__Long_Long(self.space, f1, f2)
                assert result.longval() == x * i + y * j

    def test_sub(self):
        x = 12378959520302182384345L 
        y = 88961284756491823819191823L
        for i in [-1, 1]:
            for j in [-1, 1]:
                f1 = lobj.W_LongObject(self.space, *lobj.args_from_long(x * i))
                f2 = lobj.W_LongObject(self.space, *lobj.args_from_long(y * j))
                result = lobj.sub__Long_Long(self.space, f1, f2)
                assert result.longval() == x * i - y * j

    def test_mul(self):
        x = -1238585838347L
        y = 585839391919233L
        f1 = lobj.W_LongObject(self.space, *lobj.args_from_long(x))
        f2 = lobj.W_LongObject(self.space, *lobj.args_from_long(y))
        result = lobj.mul__Long_Long(self.space, f1, f2)
        assert result.longval() == x * y



class AppTestLong:
    def test_add(self):
        assert int(123L + 12443L) == 123 + 12443
        assert -20 + 2 + 3L + True == -14

    def test_sub(self):
        assert int(58543L - 12332L) == 58543 - 12332
        assert 237123838281233L * 12 == 237123838281233L * 12L
        
    def test_mul(self):
        assert 363L * 2 ** 40 == 363L << 40
