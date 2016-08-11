import py, weakref
from rpython.rlib import revdb, rgc
from rpython.rlib.debug import debug_print
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rlib.rarithmetic import intmask
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

ASYNC_FINALIZER_TRIGGER  = 0xff46 - 2**16


def get_finalizer_queue_main():
    from rpython.rtyper.lltypesystem import lltype, rffi
    #
    from rpython.translator.tool.cbuild import ExternalCompilationInfo
    eci = ExternalCompilationInfo(
        pre_include_bits=["#define foobar(x) x\n"])
    foobar = rffi.llexternal('foobar', [lltype.Signed], lltype.Signed,
                             compilation_info=eci)
    class Glob:
        pass
    glob = Glob()
    class X:
        pass
    class MyFinalizerQueue(rgc.FinalizerQueue):
        Class = X
        def finalizer_trigger(self):
            glob.ping = True
    fq = MyFinalizerQueue()
    #
    def main(argv):
        glob.ping = False
        lst1 = [X() for i in range(256)]
        lst = [X() for i in range(3000)]
        for i, x in enumerate(lst):
            x.baz = i
            fq.register_finalizer(x)
        for i in range(3000):
            lst[i] = None
            if i % 300 == 150:
                rgc.collect()
            revdb.stop_point()
            j = i + glob.ping * 1000000
            assert foobar(j) == j
            if glob.ping:
                glob.ping = False
                total = 0
                while True:
                    x = fq.next_dead()
                    if x is None:
                        break
                    total = intmask(total * 3 + x.baz)
                assert foobar(total) == total
        keepalive_until_here(lst1)
        return 9
    return main

def get_old_style_finalizer_main():
    from rpython.rtyper.lltypesystem import lltype, rffi
    from rpython.translator.tool.cbuild import ExternalCompilationInfo
    #
    eci = ExternalCompilationInfo(
        pre_include_bits=["#define foobar(x) x\n"])
    foobar = rffi.llexternal('foobar', [lltype.Signed], lltype.Signed,
                             compilation_info=eci, _nowrapper=True)
    class Glob:
        pass
    glob = Glob()
    class X:
        def __del__(self):
            assert foobar(-7) == -7
            glob.count += 1
    def main(argv):
        glob.count = 0
        lst = [X() for i in range(3000)]
        x = -1
        for i in range(3000):
            lst[i] = None
            if i % 300 == 150:
                rgc.collect()
            revdb.stop_point()
            x = glob.count
            assert foobar(x) == x
        print x
        return 9
    return main


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
        self.compile(main, backendopt=False)
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
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # find the 2 + 16998 first WEAKREF_xxx (all "(*)" but the last two)
        for i in range(2 + 16998):
            x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_ALIVE
        for i in range(2):
            x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_prebuilt_weakref(self):
        class X:
            pass
        x1 = X()
        x1.foobar = 9
        wr = weakref.ref(x1)
        def main(argv):
            X().foobar = 43
            return wr().foobar
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # the weakref is prebuilt, so doesn't generate any WEAKREF_xxx
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_finalizer_light_ignored(self):
        py.test.skip("lightweight finalizers could be skipped, but that "
                     "requires also skipping (instead of recording) any "
                     "external call they do")
        class X:
            @rgc.must_be_light_finalizer
            def __del__(self):
                pass
        def main(argv):
            lst = [X() for i in range(3000)]
            for i in range(3000):
                lst[i] = None
                if i % 300 == 150:
                    rgc.collect()
                revdb.stop_point()
            return 9
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        x = rdb.next('q'); assert x == 3000    # number of stop points
        assert rdb.done()

    def test_finalizer_queue(self):
        main = get_finalizer_queue_main()
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        uid_seen = set()
        totals = []
        for i in range(3000):
            triggered = False
            if rdb.is_special_packet():
                time, = rdb.special_packet(ASYNC_FINALIZER_TRIGGER, 'q')
                assert time == i + 1
                y = intmask(rdb.next('q')); assert y == -1
                triggered = True
            rdb.gil_release()
            rdb.same_stack()  #
            j = rdb.next()    # call to foobar()
            rdb.gil_acquire()
            assert j == i + 1000000 * triggered
            if triggered:
                lst = []
                while True:
                    uid = intmask(rdb.next())
                    if uid == -1:
                        break
                    assert uid > 0 and uid not in uid_seen
                    uid_seen.add(uid)
                    lst.append(uid)
                rdb.gil_release()
                rdb.same_stack()                           #
                totals.append((lst, intmask(rdb.next())))  # call to foobar()
                rdb.gil_acquire()
        x = rdb.next('q'); assert x == 3000    # number of stop points
        #
        assert 1500 <= len(uid_seen) <= 3000
        d = dict(zip(sorted(uid_seen), range(len(uid_seen))))
        for lst, expected in totals:
            total = 0
            for uid in lst:
                total = intmask(total * 3 + d[uid])
            assert total == expected

    def test_old_style_finalizer(self):
        main = get_old_style_finalizer_main()
        self.compile(main, backendopt=False)
        out = self.run('Xx')
        assert 1500 < int(out) <= 3000
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        seen_uids = set()
        for i in range(3000):
            triggered = False
            if rdb.is_special_packet():
                time, = rdb.special_packet(ASYNC_FINALIZER_TRIGGER, 'q')
                assert time == i + 1
                triggered = True
                x = intmask(rdb.next())
                while True:
                    assert x != -1
                    assert x not in seen_uids
                    seen_uids.add(x)
                    rdb.same_stack()
                    y = intmask(rdb.next())
                    assert y == -7      # from the __del__
                    x = intmask(rdb.next())
                    if x == -1:
                        break
            rdb.same_stack()
            x = rdb.next()
            assert x == len(seen_uids)
        assert len(seen_uids) == int(out)
        rdb.write_call(out)
        x = rdb.next('q'); assert x == 3000    # number of stop points


class TestReplayingWeakref(InteractiveTests):
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
        compile(cls, main, backendopt=False)
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


class TestReplayingFinalizerQueue(InteractiveTests):
    expected_stop_points = 3000

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run
        main = get_finalizer_queue_main()
        compile(cls, main, backendopt=False)
        run(cls, '')

    def test_replaying_finalizer_queue(self):
        child = self.replay()
        child.send(Message(CMD_FORWARD, 3001))
        child.expect(ANSWER_AT_END)


class TestReplayingOldStyleFinalizer(InteractiveTests):
    expected_stop_points = 3000

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run
        main = get_old_style_finalizer_main()
        compile(cls, main, backendopt=False)
        run(cls, '')

    def test_replaying_old_style_finalizer(self):
        child = self.replay()
        child.send(Message(CMD_FORWARD, 3001))
        child.expect(ANSWER_AT_END)

    def test_bug1(self):
        child = self.replay()
        for i in range(50):
            child.send(Message(CMD_FORWARD, i))
            child.expect_ready()
