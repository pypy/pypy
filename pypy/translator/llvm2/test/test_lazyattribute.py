import autopath
import py

from pypy.translator.llvm.lazyattribute import *

class LazyAttributes(object):
    __metaclass__ = MetaLazyRepr
    def __init__(self, gen):
        self.gen = gen

    lazy_attributes = ["test", "test1", "test2"]

    def setup(self):
        self.test = "asdf"
        self.test1 = 23931
        self.test2 = 2 ** 2233

class PseudoGen(object):
    def __init__(self):
        self.lazy_objects = sets.Set()


class TestLazy(object):
    def setup_class(cls):
        cls.gen = PseudoGen()
        cls.la = LazyAttributes(cls.gen)

    def test_registration(self):
        assert not self.la.__setup_called__
        assert self.la in self.gen.lazy_objects

    def test_setup(self):
        print self.la.test2
        assert self.la not in self.gen.lazy_objects
        assert self.la.__setup_called__
        assert self.la.test == "asdf"
        assert self.la.test1 == 23931
        assert self.la.test2 == 2 ** 2233

    def test_attributeness(self):
        self.la.test = 23
        assert self.la.test == 23
        del self.la.test1
        py.test.raises(AttributeError, "self.la.test1")
        py.test.raises(AttributeError, "del self.la.test1")
        
    def test_type(self):
        assert type(self.la) == LazyAttributes
        assert type(type(self.la)) == MetaLazyRepr
