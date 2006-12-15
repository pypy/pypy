import py
from pypy.jit.codegen.i386.test.test_genc_ts import I386TimeshiftingTestMixin
from pypy.jit.timeshifter.test import test_timeshift
from pypy.jit.codegen.llvm.rgenop import RLLVMGenOp


class LLVMTimeshiftingTestMixin(I386TimeshiftingTestMixin):
    RGenOp = RLLVMGenOp


class TestTimeshiftLLVM(LLVMTimeshiftingTestMixin,
                        test_timeshift.TestTimeshift):

    # for the individual tests see
    # ====> ../../../timeshifter/test/test_timeshift.py

    def skip(self):
        py.test.skip("WIP")

    #passing...
    #test_very_simple = skip
    #test_convert_const_to_redbox = skip
    #test_simple_opt_const_propagation2 = skip
    #test_simple_opt_const_propagation1 = skip
    #test_loop_folding = skip
    #test_loop_merging = skip
    #test_two_loops_merging = skip
    #test_convert_greenvar_to_redvar = skip
    #test_green_across_split = skip
    #test_merge_const_before_return = skip
    #test_merge_3_redconsts_before_return = skip
    #test_arith_plus_minus = skip
    #test_plus_minus_all_inlined = skip
    #test_call_simple = skip
    #test_call_2 = skip
    #test_call_3 = skip
    #test_call_4 = skip
    #test_void_call = skip
    #test_green_call = skip
    #test_split_on_green_return = skip
    #test_recursive_call = skip
    #test_simple_indirect_call = skip
    #test_normalize_indirect_call = skip
    #test_normalize_indirect_call_more = skip
    #test_green_red_mismatch_in_call = skip
    #test_red_call_ignored_result = skip

    #failing...
    test_simple_struct = skip
    test_simple_array = skip
    test_degenerated_before_return = skip
    test_degenerated_before_return_2 = skip
    test_degenerated_at_return = skip
    test_degenerated_via_substructure = skip
    test_degenerate_with_voids = skip
    test_red_virtual_container = skip
    test_setarrayitem  = skip
    test_red_array = skip
    test_red_struct_array = skip
    test_red_varsized_struct = skip
    test_array_of_voids = skip
    test_red_propagate = skip
    test_red_subcontainer = skip
    test_red_subcontainer_cast = skip
    test_merge_structures = skip
    test_green_with_side_effects = skip
    test_recursive_with_red_termination_condition = skip
    test_simple_meth = skip
    test_simple_red_meth = skip
    test_compile_time_const_tuple = skip
    test_residual_red_call = skip
    test_residual_red_call_with_exc = skip

