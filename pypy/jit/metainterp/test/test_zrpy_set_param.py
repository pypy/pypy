import py, sys
from pypy.jit.metainterp.test import test_warmspot, test_basic
from pypy.jit.metainterp.test.test_zrpy_basic import LLInterpJitMixin


class TestLLSetParam(LLInterpJitMixin):

    test_set_param = test_basic.BasicTests.test_set_param.im_func

    test_set_param_optimizer = test_warmspot.WarmspotTests.test_set_param_optimizer.im_func
