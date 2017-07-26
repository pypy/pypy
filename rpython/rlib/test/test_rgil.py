from rpython.rlib import rgil
from rpython.translator.c.test.test_standalone import StandaloneTests


class BaseTestGIL(StandaloneTests):

    def test_simple(self):
        def main(argv):
            rgil.release()
            # don't have the GIL here
            rgil.acquire()
            rgil.yield_thread()
            print "OK"   # there is also a release/acquire pair here
            return 0

        main([])

        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert data == "OK\n"

    def test_after_thread_switch(self):
        class Foo:
            pass
        foo = Foo()
        foo.counter = 0
        def seeme():
            foo.counter += 1
        def main(argv):
            rgil.invoke_after_thread_switch(seeme)
            print "Test"     # one release/acquire pair here
            print foo.counter
            print foo.counter
            return 0

        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert data == "Test\n1\n2\n"


class TestGILAsmGcc(BaseTestGIL):
    gc = 'minimark'
    gcrootfinder = 'asmgcc'

class TestGILShadowStack(BaseTestGIL):
    gc = 'minimark'
    gcrootfinder = 'shadowstack'
