
import py
from rpython.jit.backend.test.test_rvmprof import BaseRVMProfTest
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin

class TestFfiCall(Jit386Mixin, BaseRVMProfTest):
    pass