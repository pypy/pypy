import py
from pypy.jit.backend.cli.runner import CliCPU
from pypy.jit.metainterp.test import test_basic

class CliJitMixin(test_basic.OOJitMixin):
    CPUClass = CliCPU

class TestBasic(CliJitMixin, test_basic.TestOOtype):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py

    def skip(self):
        py.test.skip("works only after translation")

    def _skip(self):
        py.test.skip("in-progress")

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
    test_instantiate_classes = skip
    test_zerodivisionerror = skip
    test_isinstance = skip
    test_oois = skip
    test_oostring_instance = skip
    
    test_stopatxpolicy = _skip
    test_bridge_from_interpreter = _skip
    test_bridge_from_interpreter_4 = _skip
