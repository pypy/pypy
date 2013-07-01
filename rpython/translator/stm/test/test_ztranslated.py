import py
from rpython.rlib import rstm, rgc
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import cast_instance_to_base_ptr
from rpython.translator.stm.test.support import CompiledSTMTests
from rpython.translator.stm.test import targetdemo2


class TestSTMTranslated(CompiledSTMTests):

    def test_malloc(self):
        class Foo:
            pass
        def entry_point(argv):
            lst = []
            for i in range(int(argv[1])):
                lst.append(Foo())
            print '<', len(lst), '>'
            return 0
        #
        t, cbuilder = self.compile(entry_point, backendopt=True)
        data = cbuilder.cmdexec('5')
        assert '< 5 >' in data, "got: %r" % (data,)
        data = cbuilder.cmdexec('42')
        assert '< 42 >' in data, "got: %r" % (data,)
        data = cbuilder.cmdexec('260')
        assert '< 260 >' in data, "got: %r" % (data,)

    def test_hash_id(self):
        from rpython.rlib.objectmodel import compute_identity_hash
        from rpython.rlib.objectmodel import compute_unique_id
        FOO = lltype.GcStruct('FOO')
        prebuilt = lltype.malloc(FOO)
        prebuilt_hash = lltype.identityhash(prebuilt)
        #
        def w(num, x):
            print '%d>>>' % num, compute_identity_hash(x), compute_unique_id(x)
        #
        def entry_point(argv):
            w(1, prebuilt)
            w(2, lltype.malloc(FOO))
            return 0
        #
        t, cbuilder = self.compile(entry_point)
        assert prebuilt_hash == lltype.identityhash(prebuilt)
        data = cbuilder.cmdexec('')
        data = data.split()
        i1 = data.index('1>>>')
        i2 = data.index('2>>>')
        int(data[i1 + 1])
        int(data[i1 + 2])
        int(data[i2 + 1])
        int(data[i2 + 2])
        assert int(data[i1 + 1]) == prebuilt_hash

    def test_start_thread(self):
        from rpython.rlib import rthread
        class Global:
            value = 1
            seen = None
        glob = Global()
        #
        def threadfn():
            x = Global()
            x.value = 0
            glob.seen = x
        def entry_point(argv):
            rstm.invoke_around_extcall()
            glob.seen = None
            rthread.start_new_thread(threadfn, ())
            while glob.seen is None:
                llop.stm_commit_transaction(lltype.Void)
                llop.stm_begin_inevitable_transaction(lltype.Void)
            return glob.seen.value
        #
        t, cbuilder = self.compile(entry_point)
        cbuilder.cmdexec('')
        # assert did not crash

    def test_become_inevitable(self):
        def entry_point(argv):
            rstm.become_inevitable()
            return 0
        t, cbuilder = self.compile(entry_point)
        cbuilder.cmdexec('')
        # assert did not crash

    def test_should_break_transaction(self):
        def entry_point(argv):
            print '<', int(rstm.should_break_transaction()), '>'
            return 0
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('')
        assert '< 1 >\n' in data

    def test_set_transaction_length(self):
        def entry_point(argv):
            rstm.set_transaction_length(123)
            return 0
        t, cbuilder = self.compile(entry_point)
        cbuilder.cmdexec('')
        # assert did not crash

    def test_stm_atomic(self):
        def entry_point(argv):
            assert not rstm.is_atomic()
            rstm.increment_atomic()
            assert rstm.is_atomic()
            rstm.decrement_atomic()
            assert not rstm.is_atomic()
            return 0
        t, cbuilder = self.compile(entry_point)
        cbuilder.cmdexec('')
        # assert did not crash

    def test_targetdemo(self):
        t, cbuilder = self.compile(targetdemo2.entry_point)
        data, dataerr = cbuilder.cmdexec('4 5000', err=True,
                                         env={'PYPY_GC_DEBUG': '1'})
        assert 'check ok!' in data

    def test_bug1(self):
        #
        class Foobar:
            pass
        def check(foobar, retry_counter):
            rgc.collect(0)
            return 0
        #
        class X:
            def __init__(self, count):
                self.count = count
        def g():
            x = X(1000)
            rstm.perform_transaction(check, Foobar, Foobar())
            return x
        def entry_point(argv):
            x = X(len(argv))
            y = g()
            print '<', x.count, y.count, '>'
            return 0
        #
        t, cbuilder = self.compile(entry_point, backendopt=True)
        data = cbuilder.cmdexec('a b c d')
        assert '< 5 1000 >' in data, "got: %r" % (data,)

    def test_bug2(self):
        #
        class Foobar:
            pass
        def check(foobar, retry_counter):
            return 0    # do nothing
        #
        class X2:
            pass
        prebuilt2 = [X2(), X2()]
        #
        def bug2(count):
            x = prebuilt2[count]
            x.foobar = 2                    # 'x' becomes a local
            #
            rstm.perform_transaction(check, Foobar, Foobar())
                                            # 'x' becomes the global again
            #
            y = prebuilt2[count]            # same prebuilt obj
            y.foobar += 10                  # 'y' becomes a local
            return x.foobar                 # read from the global, thinking
        bug2._dont_inline_ = True           #    that it is still a local
        def entry_point(argv):
            print bug2(0)
            print bug2(1)
            return 0
        #
        t, cbuilder = self.compile(entry_point, backendopt=True)
        data = cbuilder.cmdexec('')
        assert '12\n12\n' in data, "got: %r" % (data,)

    def test_prebuilt_nongc(self):
        class Foobar:
            pass
        def check(foobar, retry_counter):
            return 0    # do nothing
        from rpython.rtyper.lltypesystem import lltype
        R = lltype.GcStruct('R', ('x', lltype.Signed))
        S1 = lltype.Struct('S1', ('r', lltype.Ptr(R)))
        s1 = lltype.malloc(S1, immortal=True, flavor='raw')
        #S2 = lltype.Struct('S2', ('r', lltype.Ptr(R)),
        #                   hints={'stm_thread_local': True})
        #s2 = lltype.malloc(S2, immortal=True, flavor='raw')
        def do_stuff():
            rstm.perform_transaction(check, Foobar, Foobar())
            print s1.r.x
            #print s2.r.x
        do_stuff._dont_inline_ = True
        def main(argv):
            s1.r = lltype.malloc(R)
            s1.r.x = 42
            #s2.r = lltype.malloc(R)
            #s2.r.x = 43
            do_stuff()
            return 0
        #
        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert '42\n' in data, "got: %r" % (data,)

    def test_threadlocalref(self):
        class FooBar(object):
            pass
        t = rstm.ThreadLocalReference(FooBar)
        def main(argv):
            x = FooBar()
            assert t.get() is None
            t.set(x)
            assert t.get() is x
            print "ok"
            return 0
        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('')
        assert 'ok\n' in data

    def test_abort_info(self):
        from rpython.rtyper.lltypesystem.rclass import OBJECTPTR

        class Parent(object):
            pass
        class Foobar(Parent):
            pass
        globf = Foobar()

        def setxy(globf, retry_counter):
            if retry_counter > 1:
                globf.xy = 100 + retry_counter

        def check(_, retry_counter):
            last = rstm.charp_inspect_abort_info()
            rstm.abort_info_push(globf, ('[', 'xy', ']', 'yx'))
            setxy(globf, retry_counter)
            if retry_counter < 3:
                rstm.abort_and_retry()
            #
            print rffi.charp2str(last)
            print int(bool(rstm.charp_inspect_abort_info()))
            #
            rstm.abort_info_pop(2)
            return 0

        PS = lltype.Ptr(lltype.GcStruct('S', ('got_exception', OBJECTPTR)))
        perform_transaction = rstm.make_perform_transaction(check, PS)

        def main(argv):
            Parent().xy = 0
            globf.xy = -2
            globf.yx = 'hi there %d' % len(argv)
            perform_transaction(lltype.nullptr(PS.TO))
            return 0
        t, cbuilder = self.compile(main)
        data = cbuilder.cmdexec('a b')
        assert 'li102ee10:hi there 3e\n0\n' in data
