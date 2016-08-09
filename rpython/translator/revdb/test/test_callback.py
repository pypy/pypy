from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import revdb
from rpython.translator.revdb.test.test_basic import BaseRecordingTests
from rpython.translator.revdb.test.test_basic import InteractiveTests

from rpython.translator.revdb.message import *


def get_callback_demo():
    eci = ExternalCompilationInfo(separate_module_sources=['''
        int callme(int(*cb)(int)) {
            return cb(40) * cb(3);
        }
    '''], post_include_bits=['''
        int callme(int(*)(int));
    '''])
    FUNCPTR = lltype.Ptr(lltype.FuncType([rffi.INT], rffi.INT))
    callme = rffi.llexternal('callme', [FUNCPTR], rffi.INT,
                             compilation_info=eci)

    def callback(n):
        print intmask(n)
        return n

    def main(argv):
        revdb.stop_point()
        print intmask(callme(callback))
        revdb.stop_point()
        return 9

    return main


class TestRecording(BaseRecordingTests):

    def test_callback_simple(self):
        eci = ExternalCompilationInfo(separate_module_sources=['''
            int callme(int(*cb)(int)) {
                return cb(40) * cb(3);
            }
            int callmesimple(void) {
                return 55555;
            }
        '''], post_include_bits=['''
            int callme(int(*)(int));
            int callmesimple(void);
        '''])
        FUNCPTR = lltype.Ptr(lltype.FuncType([rffi.INT], rffi.INT))
        callme = rffi.llexternal('callme', [FUNCPTR], rffi.INT,
                                 compilation_info=eci)
        callmesimple = rffi.llexternal('callmesimple', [], rffi.INT,
                                       compilation_info=eci)

        def callback(n):
            return intmask(n) * 100

        def main(argv):
            print intmask(callmesimple())
            print intmask(callme(callback))
            return 9
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        rdb.same_stack()                        # callmesimple()
        x = rdb.next('i'); assert x == 55555
        rdb.write_call('55555\n')
        b = rdb.next('!h'); assert 300 <= b < 310  # -> callback
        x = rdb.next('i'); assert x == 40       # arg n
        x = rdb.next('!h'); assert x == b       # -> callback
        x = rdb.next('i'); assert x == 3        # arg n
        rdb.same_stack()                        # <- return in main thread
        x = rdb.next('i'); assert x == 4000 * 300   # return from callme()
        rdb.write_call('%s\n' % (4000 * 300,))
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_callback_with_effects(self):
        main = get_callback_demo()
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        b = rdb.next('!h'); assert 300 <= b < 310  # -> callback
        x = rdb.next('i'); assert x == 40       # arg n
        rdb.write_call('40\n')
        x = rdb.next('!h'); assert x == b       # -> callback again
        x = rdb.next('i'); assert x == 3        # arg n
        rdb.write_call('3\n')
        rdb.same_stack()                        # -> return in main thread
        x = rdb.next('i'); assert x == 120      # <- return from callme()
        rdb.write_call('120\n')
        x = rdb.next('q'); assert x == 2        # number of stop points
        assert rdb.done()


class TestReplayingCallback(InteractiveTests):
    expected_stop_points = 2

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run
        main = get_callback_demo()
        compile(cls, main, backendopt=False)
        run(cls, '')

    def test_replaying_callback(self):
        child = self.replay()
        child.send(Message(CMD_FORWARD, 3))
        child.expect(ANSWER_AT_END)
