from rpython.rlib import rgil
from rpython.rlib.debug import debug_print
from rpython.translator.c.test.test_standalone import StandaloneTests
from rpython.config.translationoption import get_combined_translation_config


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

    def test_am_I_holding_the_GIL(self):
        def check(name, expected=True):
            # we may not have the GIL here, don't use "print"
            debug_print(name)
            if rgil.am_I_holding_the_GIL() != expected:
                debug_print('assert failed at point', name)
                debug_print('rgil.gil_get_holder() ==', rgil.gil_get_holder())
                assert False

        def main(argv):
            check('1')
            rgil.release()
            # don't have the GIL here
            check('2', False)
            rgil.acquire()
            check('3')
            rgil.yield_thread()
            check('4')
            print "OK"   # there is also a release/acquire pair here
            check('5')
            return 0

        #main([])    -- not implemented for now

        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert data == "OK\n"



class TestGILShadowStack(BaseTestGIL):
    gc = 'minimark'
    gcrootfinder = 'shadowstack'
