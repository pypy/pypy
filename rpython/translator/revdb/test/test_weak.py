import weakref
from rpython.translator.revdb.test.test_basic import BaseRecordingTests


# Weakrefs: implemented so that the log file contains one byte
# "afterwards_alive" or "afterwards_dead" at the point where the
# weakref is created, and similarly one such byte at every point where
# the weakref is dereferenced.  At every point, the weakref is _alive_
# at the moment; but the byte tells whether it should stay alive until
# the _next_ point or not.  Done by always emitting "afterwards_dead"
# in the log, and patching that to "afterwards_alive" if later we find
# a deref() where the weakref is still alive.  (If a deref() finds the
# weakref dead, it doesn't do any recording or patching; it simply
# leaves the previous "afterwards_dead" in place.)


WEAKREF_AFTERWARDS_DEAD  = chr(0xf2)
WEAKREF_AFTERWARDS_ALIVE = chr(0xeb)


class TestRecordingWeakref(BaseRecordingTests):

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
            r1 = weakref.ref(x1)
            r2 = weakref.ref(x2)
            assert r1() is x1
            assert r2() is x2
            assert r1() is x1
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # find the five WEAKREF_xxx
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_ALIVE  # r1=ref(x1)
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_ALIVE  # r2=ref(x2)
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_ALIVE  # r1()
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD   # r2()
        x = rdb.next('c'); assert x == WEAKREF_AFTERWARDS_DEAD   # r1()
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()
