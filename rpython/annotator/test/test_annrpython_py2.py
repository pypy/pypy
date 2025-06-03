"""In which we test that various pieces of py2-only syntax are supported."""
from __future__ import with_statement

from rpython.conftest import option

from rpython.annotator import model as annmodel
from rpython.annotator.annrpython import RPythonAnnotator as _RPythonAnnotator
from rpython.translator.test import snippet

from .test_annrpython import (
    TestAnnotateTestCase as _TestAnnotateTestCase, graphof
)


class TestAnnotateTestCase:
    def teardown_method(self, meth):
        assert annmodel.s_Bool == annmodel.SomeBool()

    class RPythonAnnotator(_RPythonAnnotator):
        def build_types(self, *args):
            s = _RPythonAnnotator.build_types(self, *args)
            self.validate()
            if option.view:
                self.translator.view()
            return s

    def test_harmonic(self):
        a = self.RPythonAnnotator()
        s = a.build_types(snippet.harmonic, [int])
        assert s.knowntype == float
        # check that the list produced by range() is not mutated or resized
        graph = graphof(a, snippet.harmonic)
        all_vars = set().union(*[block.getvariables() for block in graph.iterblocks()])
        print all_vars
        for var in all_vars:
            s_value = var.annotation
            if isinstance(s_value, annmodel.SomeList):
                assert not s_value.listdef.listitem.resized
                assert not s_value.listdef.listitem.mutated
                assert s_value.listdef.listitem.range_step

    def test_prebuilt_long_that_is_not_too_long(self):
        small_constant = 12L
        def f():
            return small_constant
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.const == 12
        assert s.nonneg
        assert not s.unsigned
        #
        small_constant = -23L
        def f():
            return small_constant
        a = self.RPythonAnnotator()
        s = a.build_types(f, [])
        assert s.const == -23
        assert not s.nonneg
        assert not s.unsigned

    def test_isinstance_double_const(self):
        class X(object):
            def _freeze_(self):
                return True

        x = X()

        def f(i):
            if i:
                x1 = x
            else:
                x1 = None
            print "hello"  # this is to force the merge of blocks
            return isinstance(x1, X)

        a = self.RPythonAnnotator()
        s = a.build_types(f, [annmodel.SomeInteger()])
        assert isinstance(s, annmodel.SomeBool)
