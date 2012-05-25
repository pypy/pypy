import py
from pypy.rlib import rstm, rgc
from pypy.translator.stm.test.support import CompiledSTMTests
from pypy.translator.stm.test import targetdemo2


class TestSTMTranslated(CompiledSTMTests):

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
        from pypy.rpython.lltypesystem import lltype
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
