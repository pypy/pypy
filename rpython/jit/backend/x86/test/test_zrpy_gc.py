from rpython.jit.backend.llsupport.test.zrpy_gc_test import CompileFrameworkTests


class TestShadowStack(CompileFrameworkTests):
    gcrootfinder = "shadowstack"
    gc = "incminimark"


class TestRemoteHeaderShadowStack(CompileFrameworkTests):
    gcrootfinder = "shadowstack"
    gc = "incminimark_remoteheader"
