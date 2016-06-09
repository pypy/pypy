
from rpython.jit.backend.llsupport.test.zrpy_vmprof_test import CompiledVmprofTest

class TestZVMprof(CompiledVmprofTest):
    gcrootfinder = "shadowstack"
    gc = "incminimark"

class TestRemoteHeaderZVMprof(CompiledVmprofTest):
    gcrootfinder = "shadowstack"
    gc = "incminimark_remoteheader"
