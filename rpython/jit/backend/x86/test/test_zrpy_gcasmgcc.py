from rpython.jit.backend.llsupport.test.zrpy_gc_test import CompileFrameworkTests

class TestAsmGcc(CompileFrameworkTests):
    gcrootfinder = "asmgcc"
