import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.metainterp.test import test_basic

class CliJitMixin(test_basic.OOJitMixin):
    CPUClass = CliCPU
    def setup_class(cls):
        from pypy.translator.cli.support import PythonNet
        PythonNet.System     # possibly raises Skip

class TestBasic(CliJitMixin, test_basic.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py

    def skip(self):
        py.test.skip("works only after translation")

    test_string = skip
    test_chr2str = skip
    test_unicode = skip
    test_residual_call = skip
    test_constant_across_mp = skip
    test_format = skip
    test_getfield = skip
    test_getfield_immutable = skip
    test_print = skip
    test_bridge_from_interpreter_2 = skip
    test_bridge_from_interpreter_3 = skip
    test_bridge_leaving_interpreter_5 = skip
    test_instantiate_classes = skip
    test_zerodivisionerror = skip
    test_isinstance = skip
    test_isinstance_2 = skip
    test_oois = skip
    test_oostring_instance = skip
    test_long_long = skip
    test_free_object = skip
    test_stopatxpolicy = skip
    test_residual_call_pure = skip
    test_div_overflow = skip
    test_subclassof = skip
    test_assert_isinstance = skip
    test_dont_look_inside = skip
    test_setfield_bool = skip
    test_instantiate_does_not_call = skip
    test_listcomp = skip
    test_tuple_immutable = skip
    test_oosend_look_inside_only_one = skip
    test_residual_external_call = skip
    test_merge_guardclass_guardvalue = skip
    test_merge_guardnonnull_guardclass = skip
    test_merge_guardnonnull_guardvalue = skip
    test_merge_guardnonnull_guardvalue_2 = skip
    test_merge_guardnonnull_guardclass_guardvalue = skip
    test_residual_call_doesnt_lose_info = skip
    test_oohash = skip
    test_identityhash = skip
    test_guard_isnull_nonnull = skip
    test_r_dict = skip
