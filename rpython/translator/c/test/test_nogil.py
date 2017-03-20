import py
import os

from rpython.translator.translator import TranslationContext
from rpython.translator.c.genc import CStandaloneBuilder

from rpython.annotator.listdef import s_list_of_strings







class TestThread(object):
    gcrootfinder = 'shadowstack'
    config = None

    def compile(self, entry_point, no__thread=False):
        t = TranslationContext(self.config)
        t.config.translation.gc = "incminimark"
        t.config.translation.gcrootfinder = self.gcrootfinder
        t.config.translation.thread = True
        t.config.translation.no__thread = no__thread
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()
        #
        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        cbuilder.compile()
        #
        return t, cbuilder



    def test_concurrent_allocate(self):
        import time
        from rpython.rlib import rthread, rposix

        class X:
            def __init__(self, prev, i):
                self.prev = prev
                self.i = i

        class State:
            pass
        state = State()

        def thread():
            rthread.gc_thread_start()
            x = None
            for i in range(100000000):
                prev_x = x

                x = X(x, i)

                if prev_x is not None:
                    assert prev_x.i == i - 1

                if i % 5001 == 0:
                    x = None

            state.lock.acquire(True)
            os.write(1, "counter=%d\n" % state.counter)
            state.counter -= 1
            state.lock.release()
            rthread.gc_thread_die()

        def entry_point(argv):
            os.write(1, "hello world\n")
            # start 5 new threads
            TS = int(argv[1])
            state.lock = rthread.allocate_lock()
            state.counter = TS

            for _ in range(TS):
                rthread.start_new_thread(thread, ())

            i = 0
            while True:
                x = X(None, i)
                time.sleep(0.1)
                assert x.i == i
                if state.counter == 0:
                    break
                i += 1
            os.write(1, "all threads done\n")
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('5')
        assert data.splitlines() == ['hello world',
                                     'counter=5',
                                     'counter=4',
                                     'counter=3',
                                     'counter=2',
                                     'counter=1',
                                     'all threads done']
