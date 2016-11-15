from rpython.jit.backend.llsupport.test.zrpy_releasegil_test import ReleaseGILTests
from rpython.translator.platform import platform as compiler


class TestShadowStack(ReleaseGILTests):
    gcrootfinder = "shadowstack"


if compiler.name != 'msvc':
    class TestAsmGcc(ReleaseGILTests):
        gcrootfinder = "asmgcc"
