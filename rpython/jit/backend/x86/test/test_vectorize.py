import py
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.warmspot import ll_meta_interp
from rpython.jit.metainterp.test import support, test_vectorize
from rpython.jit.backend.x86.test import test_basic
from rpython.rlib.jit import JitDriver


class TestBasic(test_basic.Jit386Mixin, test_vectorize.VectorizeLLtypeTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_basic.py
    pass
