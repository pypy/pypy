from pypy.translator.c.test import test_standalone

class TestThreadedAsmGcc(test_standalone.TestThread):
    gcrootfinder = 'asmgcc'
