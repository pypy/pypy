
import autopath
from pypy.annotation.model import *


s1 = SomeObject()
s2 = SomeInteger(nonneg=True)
s3 = SomeInteger(nonneg=False)
s4 = SomeList({}, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
s5 = SomeList({}, SomeTuple([SomeInteger(nonneg=False), SomeString()]))
s6 = SomeImpossibleValue()
slist = [s1,s2,s3,s4,s5,s6]

def test_equality():
    assert s1 != s2 != s3 != s4 != s5 != s6
    assert s1 == SomeObject()
    assert s2 == SomeInteger(nonneg=True)
    assert s3 == SomeInteger(nonneg=False)
    assert s4 == SomeList({}, SomeTuple([SomeInteger(nonneg=True), SomeString()]))
    assert s5 == SomeList({}, SomeTuple([SomeInteger(nonneg=False), SomeString()]))
    assert s6 == SomeImpossibleValue()

def test_contains():
    assert ([(s,t) for s in slist for t in slist if s.contains(t)] ==
            [(s1,s1), (s1,s2), (s1,s3), (s1,s4), (s1,s5), (s1,s6),
                      (s2,s2),                            (s2,s6),
                      (s3,s2), (s3,s3),                   (s3,s6),
                                        (s4,s4),          (s4,s6),
                                        (s5,s4), (s5,s5), (s5,s6),
                                                          (s6,s6)])

def test_union():
    assert ([unionof(s,t) for s in slist for t in slist] ==
            [s1, s1, s1, s1, s1, s1,
             s1, s2, s3, s1, s1, s2,
             s1, s3, s3, s1, s1, s3,
             s1, s1, s1, s4, s5, s4,
             s1, s1, s1, s5, s5, s5,
             s1, s2, s3, s4, s5, s6])


if __name__ == '__main__':
    for name, value in globals().items():
        if name.startswith('test_'):
            value()
