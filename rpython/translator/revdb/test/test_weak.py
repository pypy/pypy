import weakref
from rpython.rlib import revdb, rgc
from rpython.rlib.debug import debug_print
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.translator.revdb.message import *
from rpython.translator.revdb.test.test_basic import BaseRecordingTests
from rpython.translator.revdb.test.test_basic import InteractiveTests


# Weakrefs: implemented so that the log file contains one byte
# "afterwards_alive" or "afterwards_dead" at the point where the
# weakref is created, and similarly one such byte at every point where
# the weakref is dereferenced.  At every point, the weakref is _alive_
# at the moment; but the byte tells whether it should stay alive until
# the _next_ point or not.  Done by always emitting "afterwards_dead"
# in the log, and patching that to "afterwards_alive" if later we find
# a deref() where the weakref is still alive.  (If a deref() finds the
# weakref dead, it doesn't do any recording or patching; it simply
# leaves the previous already-written "afterwards_dead" byte.)


WEAKREF_AFTERWARDS_DEAD  = chr(0xf2)
WEAKREF_AFTERWARDS_ALIVE = chr(0xeb)


class TestRecording(BaseRecordingTests):

    def test_weakref_create(self):
        class X:
            pass
        class Glob:
            pass
        glob = Glob()
        def main(argv):
            glob.r1 = weakref.ref(X())
            glob.r2 = weakref.ref(X())
            glob.r3 = weakref.ref(X())
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # find the extra WEAKREF_DEAD
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_weakref_deref_nondead(self):
        class X:
            pass
        class Glob:
            pass
        glob = Glob()
        def main(argv):
            x1 = X(); x2 = X()
            r1 = weakref.ref(x1)     # (*)
            r2 = weakref.ref(x2)     # (*)
            for i in range(8500):
                assert r1() is x1    # (*)
                assert r2() is x2    # (*)
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # find the 2 + 16998 first WEAKREF_xxx (all "(*)" but the last two)
        for i in range(2 + 16998):
            x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_ALIVE
        for i in range(2):
            x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_finalizer_light_ignored(self):
        class X:
            @rgc.must_be_light_finalizer
            def __del__(self):
                pass
        def main(argv):
            lst = [X() for i in range(3000)]
            for i in range(3000):
                lst[i] = None
                revdb.stop_point()
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        x = rdb.next('q'); assert x == 3000    # number of stop points
        assert rdb.done()


class TestReplaying(InteractiveTests):
    expected_stop_points = 1

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run

        class X:
            def __init__(self, s):
                self.s = s
        prebuilt = X('prebuilt')

        def make(s):
            lst = [prebuilt] + [X(c) for c in s]
            keepalive = lst[-1]
            return [weakref.ref(x) for x in lst], keepalive

        def main(argv):
            lst, keepalive = make(argv[0])
            expected = ['prebuilt'] + [c for c in argv[0]]
            dead = [False] * len(lst)
            for j in range(17000):
                outp = []
                for i in range(len(lst)):
                    v = lst[i]()
                    debug_print(v)
                    if dead[i]:
                        assert v is None
                    elif v is None:
                        outp.append('<DEAD>')
                        dead[i] = True
                    else:
                        outp.append(v.s)
                        assert v.s == expected[i]
                print ''.join(outp)
                if (j % 1000) == 999:
                    debug_print('============= COLLECT ===========')
                    rgc.collect()
                debug_print('------ done', j, '.')
            assert not dead[0]
            assert not dead[-1]
            keepalive_until_here(keepalive)
            revdb.stop_point()
            return 9
        compile(cls, main, [], backendopt=False)
        output = run(cls, '')
        lines = output.splitlines()
        assert lines[-1].startswith('prebuilt') and lines[-1].endswith(
            str(cls.exename)[-1])
        assert (len(lines[-1]) + output.count('<DEAD>') ==
                len('prebuilt') + len(str(cls.exename)))

    def test_replaying_weakref(self):
        child = self.replay()
        # the asserts are replayed; if we get here it means they passed again
        child.send(Message(CMD_FORWARD, 1))
        child.expect(ANSWER_AT_END)
