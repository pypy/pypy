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
        'test_hide_and_reveal_p',
        'test_largedummy_direct', # _compile works if we set a higher maxstack
        'test_branching',
        'test_goto',
        'test_if',
        # 'test_switch',              # no promotion/flexswitch for now please :-)
        # 'test_defaultonly_switch',  # the same
        'test_fact',
        'test_calling_pause',
        'test_longwinded_and',
        'test_condition_result_cross_link_direct',
        'test_multiple_cmps',
        'test_flipped_cmp_with_immediate',
        'test_tight_loop',
        'test_jump_to_block_with_many_vars',
        'test_same_as',
        'test_pause_and_resume',
        'test_like_residual_red_call_with_exc',
        'test_call_functions_with_different_signatures',
        'test_bool_not_direct',
        # 'test_read_frame_var',     # not for now
        # 'test_write_frame_place',
        # 'test_write_lots_of_frame_places_direct',
        # 'test_read_frame_place_direct',
        # 'test_read_frame_place_compile'
        # 'test_frame_vars_like_the_frontend_direct',
        'test_unaliasing_variables_direct',
        # 'test_from_random_direct',  # mono crashes
        'test_from_random_2_direct',
        # 'test_from_random_3_direct', # we need yet another delegate type
        'test_from_random_4_direct',
        # 'test_from_random_5_direct', # we need yet another delegate type
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
