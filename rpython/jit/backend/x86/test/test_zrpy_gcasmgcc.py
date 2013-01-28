
from rpython.jit.backend.x86.test.test_zrpy_gc import CompileFrameworkTests

class TestAsmGcc(CompileFrameworkTests):
    gcrootfinder = "asmgcc"
