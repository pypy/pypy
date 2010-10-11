import py
from pypy.config.translationoption import IS_64_BITS
from pypy.rpython.test import test_rclass
from pypy.rpython import rmodel, rint, rclass
from pypy.rpython.lltypesystem import llmemory


def setup_module(mod):
    if not IS_64_BITS:
        py.test.skip("for 64-bits only")


class MixinCompressed64(object):
    def _get_config(self):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.compressptr = True
        return config

    def interpret(self, *args, **kwds):
        kwds['config'] = self._get_config()
        return super(MixinCompressed64, self).interpret(*args, **kwds)

    def interpret_raises(self, *args, **kwds):
        kwds['config'] = self._get_config()
        return super(MixinCompressed64, self).interpret_raises(*args, **kwds)


class TestExternalVsInternal(MixinCompressed64):
    def setup_method(self, _):
        class FakeRTyper(object):
            class annotator:
                class translator:
                    config = self._get_config()
            class type_system:
                from pypy.rpython.lltypesystem import rclass
            def add_pendingsetup(self, r):
                pass
        self.rtyper = FakeRTyper()
        self.rtyper.instance_reprs = {}

    def get_r_A(self):
        class FakeClassDesc:
            pyobj = None
            def read_attribute(self, name, default):
                return default
        class FakeClassDef(object):
            classdesc = FakeClassDesc()
            def getallsubdefs(self):
                return [self]
        classdef = FakeClassDef()
        return rclass.getinstancerepr(self.rtyper, classdef)

    def get_r_L(self, itemrepr, fixed=True):
        from pypy.rpython.lltypesystem import rlist
        class FakeListItem(object):
            pass
        if fixed:
            cls = rlist.FixedSizeListRepr
        else:
            cls = rlist.ListRepr
        return cls(self.rtyper, itemrepr, FakeListItem())

    def test_simple(self):
        er, ir = rmodel.externalvsinternal(self.rtyper, rint.signed_repr)
        assert er is ir is rint.signed_repr
        er, ir = rmodel.externalvsinternalfield(self.rtyper, rint.signed_repr)
        assert er is ir is rint.signed_repr

    def test_instance(self):
        r_A = self.get_r_A()
        er, ir = rmodel.externalvsinternal(self.rtyper, r_A)
        assert er is r_A
        assert ir.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_A)
        assert er is r_A
        assert ir.lowleveltype == llmemory.HiddenGcRef32

    def test_fixedlist_of_ints(self):
        r_L = self.get_r_L(rint.signed_repr)
        assert r_L.lowleveltype.TO._is_varsize()
        assert r_L.external_item_repr is rint.signed_repr
        assert r_L.item_repr is rint.signed_repr
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is ir is r_L
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is ir is r_L

    def test_varlist_of_ints(self):
        r_L = self.get_r_L(rint.signed_repr, fixed=False)
        assert r_L.external_item_repr is rint.signed_repr
        assert r_L.item_repr is rint.signed_repr
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32

    def test_fixedlist_of_instance(self):
        r_A = self.get_r_A()
        r_L = self.get_r_L(r_A)
        assert r_L.external_item_repr is r_A
        assert r_L.item_repr.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is ir is r_L
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is ir is r_L

    def test_varlist_of_instance(self):
        r_A = self.get_r_A()
        r_L = self.get_r_L(r_A, fixed=False)
        assert r_L.external_item_repr is r_A
        assert r_L.item_repr.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32

    def test_fixedlist_of_fixedlist_of_instance(self):
        r_A = self.get_r_A()
        r_L1 = self.get_r_L(r_A)
        r_L = self.get_r_L(r_L1)
        assert r_L.external_item_repr is r_L1
        assert r_L.item_repr is r_L1
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is ir is r_L
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is ir is r_L

    def test_fixedlist_of_varlist_of_instance(self):
        r_A = self.get_r_A()
        r_L1 = self.get_r_L(r_A, fixed=False)
        r_L = self.get_r_L(r_L1)
        assert r_L.external_item_repr is r_L1
        assert r_L.item_repr.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is ir is r_L
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is ir is r_L

    def test_varlist_of_fixedlist_of_instance(self):
        r_A = self.get_r_A()
        r_L1 = self.get_r_L(r_A)
        r_L = self.get_r_L(r_L1, fixed=False)
        assert r_L.external_item_repr is r_L1
        assert r_L.item_repr is r_L1
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32

    def test_varlist_of_varlist_of_instance(self):
        r_A = self.get_r_A()
        r_L1 = self.get_r_L(r_A, fixed=False)
        r_L = self.get_r_L(r_L1, fixed=False)
        assert r_L.external_item_repr is r_L1
        assert r_L.item_repr.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternal(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32
        er, ir = rmodel.externalvsinternalfield(self.rtyper, r_L)
        assert er is r_L
        assert ir.lowleveltype == llmemory.HiddenGcRef32


class TestLLtype64(MixinCompressed64, test_rclass.TestLLtype):

    def test_casts_1(self):
        class A:
            pass
        class B(A):
            pass
        def dummyfn(n):
            if n > 5:
                # this tuple is allocated as a (*, Void) tuple, and immediately
                # converted into a generic (*, *) tuple.
                x = (B(), None)
            else:
                x = (A(), A())
            return x[0]
        res = self.interpret(dummyfn, [8])
        assert self.is_of_instance_type(res)

    def test_dict_recast(self):
        from pypy.rlib.objectmodel import r_dict
        class A(object):
            pass
        def myeq(n, m):
            return n == m
        def myhash(a):
            return 42
        def fn():
            d = r_dict(myeq, myhash)
            d[4] = A()
            a = d.values()[0]
            a.x = 5
        self.interpret(fn, [])

    def test_dict_recast_2(self):
        from pypy.rlib.objectmodel import r_dict
        def fn():
            d = {4: 5}
            return d.items()[0][1]
        res = self.interpret(fn, [])
        assert res == 5

    def test_tuple_eq(self):
        base = (5, (6, (7,)))
        def fn(i, j, k):
            return (i, (j, (k,))) == base
        res = self.interpret(fn, [5, 6, 7])
        assert res == True
        res = self.interpret(fn, [5, 6, 8])
        assert res == False
