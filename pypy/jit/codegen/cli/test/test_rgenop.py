import py
from pypy.rpython.ootypesystem import ootype
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests, OOType
from pypy.translator.cli.test.runtest import compile_function

class TestRCliGenop(AbstractRGenOpTests):
    RGenOp = RCliGenOp
    T = OOType

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py

    def getcompiled(self, fn, annotation, annotatorpolicy):
        return compile_function(fn, annotation,
                                annotatorpolicy=annotatorpolicy,
                                nowrap=False)

    def cast(self, gv, nb_args):
        "NOT_RPYTHON"
        def fn(*args):
            return gv.getobj().func.Invoke(*args)
        return fn

    def directtesthelper(self, FUNCTYPE, func):
        py.test.skip('???')

    def test_largedummy_compile(self):
        py.test.skip('it works only if we increase .maxstack')

    def test_switch_direct(self):
        py.test.skip('no promotion/flexswitch for now please :-)')

    def test_switch_compile(self):
        py.test.skip('no promotion/flexswitch for now please :-)')

    def test_large_switch_direct(self):
        py.test.skip('no promotion/flexswitch for now please :-)')

    def test_large_switch_compile(self):
        py.test.skip('no promotion/flexswitch for now please :-)')

    def test_defaultonly_switch(self):
        py.test.skip('no promotion/flexswitch for now please :-)')

    def test_read_frame_var_direct(self):
        py.test.skip('fixme: add support for frames')

    def test_read_frame_var_compile(self):
        py.test.skip('fixme: add support for frames')

    def test_write_frame_place_direct(self):
        py.test.skip('fixme: add support for frames')

    def test_write_frame_place_compile(self):
        py.test.skip('fixme: add support for frames')

    def test_write_lots_of_frame_places_direct(self):
        py.test.skip('fixme: add support for frames')
        
    def test_read_frame_place_direct(self):
        py.test.skip('fixme: add support for frames')
        
    def test_read_frame_place_compile(self):
        py.test.skip('fixme: add support for frames')
        
    def test_frame_vars_like_the_frontend_direct(self):
        py.test.skip('fixme: add support for frames')

    def test_from_random_direct(self):
        py.test.skip('mono crashes')
        
    def test_from_random_3_direct(self):
        py.test.skip('infinite loop')
        
    def test_from_random_5_direct(self):
        py.test.skip('mono crash')

    def test_genzeroconst(self):
        py.test.skip('fixme')

    def test_ovfcheck_adder_direct(self):
        py.test.skip('fixme')

    def test_ovfcheck_adder_compile(self):
        py.test.skip('fixme')

    def test_ovfcheck1_direct(self):
        py.test.skip('fixme')

    def test_ovfcheck1_compile(self):
        py.test.skip('fixme')

    def test_ovfcheck2_direct(self):
        py.test.skip('fixme')

    def test_cast_direct(self):
        py.test.skip('fixme')

    def test_array_of_ints(self):
        py.test.skip('fixme')

    def test_interior_access(self):
        py.test.skip('fixme')
