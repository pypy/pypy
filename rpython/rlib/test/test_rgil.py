from rpython.rlib import rgil
from rpython.translator.c.test.test_standalone import StandaloneTests


class BaseTestGIL(StandaloneTests):

    def test_simple(self):
        def main(argv):
            rgil.gil_allocate()
            rgil.release()
            # don't have the GIL here
            rgil.acquire()
            print "OK"   # there is also a release/acquire pair here
            return 0

        main([])

        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert data == "OK\n"


class TestGILAsmGcc(BaseTestGIL):
    gc = 'minimark'
    gcrootfinder = 'asmgcc'

class TestGILShadowStack(BaseTestGIL):
    gc = 'minimark'
    gcrootfinder = 'shadowstack'
