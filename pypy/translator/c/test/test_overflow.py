
""" This is a test that should be in rpython directory. The thing is that
on top of llinterp these tests take forever, so they're here. They usually
segfault when run on top of C, hence inheritance from AbstractGCTestClass
"""

import py
from pypy.translator.c.test.test_boehm import AbstractGCTestClass

class TestOverflow(AbstractGCTestClass):
    def test_ll_join_strs(self):
        def f(i):
            x = "A" * (2 << i)
            ''.join([x] * (2 << i))

        fn = self.getcompiled(f, [int])
        py.test.raises(OverflowError, fn, 16)
        # XXX - we cannot grab overflow check inside test, for obscure
        #       graph related reasons it gets propagated anyway

    def test_ll_join(self):
        def f(i):
            x = "A" * (2 << i)
            'a'.join([x] * (2 << i))

        fn = self.getcompiled(f, [int])
        py.test.raises(OverflowError, fn, 16)
            
