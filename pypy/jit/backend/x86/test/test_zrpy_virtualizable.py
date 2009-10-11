
import py
from pypy.jit.metainterp.test import test_virtualizable
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin


class TestLLImplicitVirtualizable(Jit386Mixin,
                       test_virtualizable.ImplicitVirtualizableTests):
    slow = True
