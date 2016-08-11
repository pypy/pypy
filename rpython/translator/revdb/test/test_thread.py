from rpython.translator.revdb.test.test_basic import BaseRecordingTests
from rpython.translator.revdb.test.test_basic import InteractiveTests
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib import rthread
from rpython.rlib import revdb

from rpython.translator.revdb.message import *


_sleep = rffi.llexternal('sleep', [rffi.UINT], rffi.UINT)


class TestThreadRecording(BaseRecordingTests):

    def test_thread_simple(self):
        def bootstrap():
            rthread.gc_thread_start()
            _sleep(1)
            print "BB"
            _sleep(2)
            print "BBB"
            rthread.gc_thread_die()

        def main(argv):
            print "A"
            rthread.start_new_thread(bootstrap, ())
            for i in range(2):
                _sleep(2)
                print "AAAA"
            return 9

        self.compile(main, backendopt=False, thread=True)
        out = self.run('Xx')
        # should have printed A, BB, AAAA, BBB, AAAA
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        th_A = rdb.main_thread_id
        rdb.write_call("A\n")
        rdb.same_stack()      # RPyGilAllocate()
        rdb.gil_release()

        th_B = rdb.switch_thread()
        assert th_B != th_A
        b = rdb.next('!h'); assert 300 <= b < 310   # "callback": start thread
        rdb.gil_acquire()
        rdb.gil_release()

        rdb.switch_thread(th_A)
        rdb.same_stack()      # start_new_thread returns
        x = rdb.next(); assert x == th_B    # result is the 'th_B' id
        rdb.gil_acquire()
        rdb.gil_release()

        rdb.switch_thread(th_B)
        rdb.same_stack()      # sleep() (finishes here)
        rdb.next('i')         # sleep()
        rdb.gil_acquire()
        rdb.write_call("BB\n")
        rdb.gil_release()

        rdb.switch_thread(th_A)
        rdb.same_stack()      # sleep()
        rdb.next('i')         # sleep()
        rdb.gil_acquire()
        rdb.write_call("AAAA\n")
        rdb.gil_release()

        rdb.switch_thread(th_B)
        rdb.same_stack()      # sleep()
        rdb.next('i')         # sleep()
        rdb.gil_acquire()
        rdb.write_call("BBB\n")
        rdb.gil_release()

        rdb.switch_thread(th_A)
        rdb.same_stack()      # sleep()
        rdb.next('i')         # sleep()
        rdb.gil_acquire()
        rdb.write_call("AAAA\n")
        rdb.done()


class TestThreadInteractive(InteractiveTests):
    expected_stop_points = 5

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run
        def bootstrap():
            rthread.gc_thread_start()
            _sleep(1)
            revdb.stop_point()
            _sleep(2)
            revdb.stop_point()
            rthread.gc_thread_die()

        def main(argv):
            revdb.stop_point()
            rthread.start_new_thread(bootstrap, ())
            for i in range(2):
                _sleep(2)
                revdb.stop_point()
            print "ok"
            return 9

        compile(cls, main, backendopt=False, thread=True)
        assert run(cls, '') == 'ok\n'

    def test_go(self):
        child = self.replay()
        for i in range(2, 6):
            child.send(Message(CMD_FORWARD, 1))
            child.expect(ANSWER_READY, i, Ellipsis)
        child.send(Message(CMD_FORWARD, 1))
        child.expect(ANSWER_AT_END)
