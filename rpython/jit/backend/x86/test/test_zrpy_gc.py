from rpython.jit.backend.llsupport.test.zrpy_gc_test import CompileFrameworkTests


class TestSTMShadowStack(CompileFrameworkTests):
    gcrootfinder = "stm"


class TestShadowStack(CompileFrameworkTests):
    gcrootfinder = "shadowstack"
