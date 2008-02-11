import py
from pypy.rpython.ootypesystem import ootype
from pypy.jit.codegen.cli.rgenop import RCliGenOp
from pypy.jit.codegen.test.rgenop_tests import AbstractRGenOpTests, OOType
from pypy.translator.cli.test.runtest import compile_function

passing = set()
def fn():
    prefixes = [
        'test_adder',
        'test_dummy',
        'test_hide_and_reveal',
        # 'test_hide_and_reveal_p', # think about this
        'test_largedummy_direct', # _compile works if we set a higher maxstack
        'test_branching',
        'test_goto',
        'test_if',
        # 'test_switch', # no promotion/flexswitch for now please :-)
        'test_fact',
        'test_calling_pause',
        'test_longwinded_and',
        'test_condition_result_cross_link_direct',
        'test_multiple_cmps',
        'test_flipped_cmp_with_immediate',
        'test_tight_loop',
        'test_jump_to_block_with_many_vars',
        ]

    for p in prefixes:
        passing.add(p)
        passing.add(p + '_direct')
        passing.add(p + '_compile')
fn()
del fn

class TestRCliGenop(AbstractRGenOpTests):
    RGenOp = RCliGenOp
    T = OOType

    # for the individual tests see
    # ====> ../../test/rgenop_tests.py

    def getcompiled(self, fn, annotation, annotatorpolicy):
        return compile_function(fn, annotation,
                                annotatorpolicy=annotatorpolicy,
                                nowrap=True)

    def cast(self, gv, nb_args):
        "NOT_RPYTHON"
        def fn(*args):
            return gv.getobj().Invoke(*args)
        return fn

    def directtesthelper(self, FUNCTYPE, func):
        py.test.skip('???')

    def __getattribute__(self, name):
        if name.startswith('test_') and name not in passing:
            def fn():
                py.test.skip("doesn't work yet")
            return fn
        else:
            return object.__getattribute__(self, name)
