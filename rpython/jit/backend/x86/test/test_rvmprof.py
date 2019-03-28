
import py
from rpython.jit.backend.test.test_rvmprof import BaseRVMProfTest
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin

class TestRVMProfCall(Jit386Mixin, BaseRVMProfTest):
    pass
