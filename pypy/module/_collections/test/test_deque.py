import py
from pypy.conftest import gettestobjspace

class AppTestBasic:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_collections'])

    def test_basics(self):
        from _collections import deque
        d = deque(xrange(-5125, -5000))
        d.__init__(xrange(200))
        for i in xrange(200, 400):
            d.append(i)
        for i in reversed(xrange(-200, 0)):
            d.appendleft(i)
        assert list(d) == range(-200, 400)
        assert len(d) == 600

        left = [d.popleft() for i in xrange(250)]
        assert left == range(-200, 50)
        assert list(d) == range(50, 400)

        right = [d.pop() for i in xrange(250)]
        right.reverse()
        assert right == range(150, 400)
        assert list(d) == range(50, 150)

    def test_maxlen(self):
        from _collections import deque
        raises(ValueError, deque, 'abc', -1)
        raises(ValueError, deque, 'abc', -2)
        it = iter(range(10))
        d = deque(it, maxlen=3)
        assert list(it) == []
        assert repr(d) == 'deque([7, 8, 9], maxlen=3)'
        assert list(d) == range(7, 10)
        d.appendleft(3)
        assert list(d) == [3, 7, 8]
        d.extend([20, 21])
        assert list(d) == [8, 20, 21]
        d.extendleft([-7, -6])
        assert list(d) == [-6, -7, 8]

    def test_maxlen_zero(self):
        from _collections import deque
        it = iter(range(100))
        d = deque(it, maxlen=0)
        assert list(d) == []
        assert list(it) == []
        d.extend(range(100))
        assert list(d) == []
        d.extendleft(range(100))
        assert list(d) == []

    def test_maxlen_attribute(self):
        from _collections import deque
        assert deque().maxlen is None
        assert deque('abc').maxlen is None
        assert deque('abc', maxlen=4).maxlen == 4
        assert deque('abc', maxlen=0).maxlen == 0
        raises((AttributeError, TypeError), "deque('abc').maxlen = 10")

    def test_runtimeerror(self):
        from _collections import deque
        d = deque('abcdefg')
        it = iter(d)
        d.pop()
        raises(RuntimeError, it.next)
        #
        d = deque('abcdefg')
        it = iter(d)
        d.append(d.pop())
        raises(RuntimeError, it.next)
        #
        d = deque()
        it = iter(d)
        d.append(10)
        raises(RuntimeError, it.next)

    def test_count(self):
        from _collections import deque
        for s in ('', 'abracadabra', 'simsalabim'*50+'abc'):
            s = list(s)
            d = deque(s)
            for letter in 'abcdeilmrs':
                assert s.count(letter) == d.count(letter)
        class MutatingCompare:
            def __eq__(self, other):
                d.pop()
                return True
        m = MutatingCompare()
        d = deque([1, 2, 3, m, 4, 5])
        raises(RuntimeError, d.count, 3)

    def test_comparisons(self):
        from _collections import deque
        d = deque('xabc'); d.popleft()
        for e in [d, deque('abc'), deque('ab'), deque(), list(d)]:
            assert (d==e) == (type(d)==type(e) and list(d)==list(e))
            assert (d!=e) == (not(type(d)==type(e) and list(d)==list(e)))

        args = map(deque, ('', 'a', 'b', 'ab', 'ba', 'abc', 'xba', 'xabc', 'cba'))
        for x in args:
            for y in args:
                assert (x == y) == (list(x) == list(y))
                assert (x != y) == (list(x) != list(y))
                assert (x <  y) == (list(x) <  list(y))
                assert (x <= y) == (list(x) <= list(y))
                assert (x >  y) == (list(x) >  list(y))
                assert (x >= y) == (list(x) >= list(y))
                assert cmp(x,y) == cmp(list(x),list(y))

    def test_extend(self):
        from _collections import deque
        d = deque('a')
        d.extend('bcd')
        assert list(d) == list('abcd')
        d.extend(d)
        assert list(d) == list('abcdabcd')

    def test_iadd(self):
        from _collections import deque
        d = deque('a')
        original_d = d
        d += 'bcd'
        assert list(d) == list('abcd')
        d += d
        assert list(d) == list('abcdabcd')
        assert original_d is d

    def test_extendleft(self):
        from _collections import deque
        d = deque('a')
        d.extendleft('bcd')
        assert list(d) == list(reversed('abcd'))
        d.extendleft(d)
        assert list(d) == list('abcddcba')

    def test_getitem(self):
        from _collections import deque
        n = 200
        l = xrange(1000, 1000 + n)
        d = deque(l)
        for j in xrange(-n, n):
            assert d[j] == l[j]
        raises(IndexError, "d[-n-1]")
        raises(IndexError, "d[n]")

    def test_setitem(self):
        from _collections import deque
        n = 200
        d = deque(xrange(n))
        for i in xrange(n):
            d[i] = 10 * i
        assert list(d) == [10*i for i in xrange(n)]
        l = list(d)
        for i in xrange(1-n, 0, -3):
            d[i] = 7*i
            l[i] = 7*i
        assert list(d) == l

    def test_delitem(self):
        from _collections import deque
        d = deque("abcdef")
        del d[-2]
        assert list(d) == list("abcdf")

    def test_reverse(self):
        from _collections import deque
        d = deque(xrange(1000, 1200))
        d.reverse()
        assert list(d) == list(reversed(range(1000, 1200)))

    def test_rotate(self):
        from _collections import deque
        s = tuple('abcde')
        n = len(s)

        d = deque(s)
        d.rotate(1)             # verify rot(1)
        assert ''.join(d) == 'eabcd'

        d = deque(s)
        d.rotate(-1)            # verify rot(-1)
        assert ''.join(d) == 'bcdea'
        d.rotate()              # check default to 1
        assert tuple(d) == s

        d.rotate(500000002)
        assert tuple(d) == tuple('deabc')
        d.rotate(-5000002)
        assert tuple(d) == tuple(s)

    def test_len(self):
        from _collections import deque
        d = deque('ab')
        assert len(d) == 2
        d.popleft()
        assert len(d) == 1
        d.pop()
        assert len(d) == 0
        raises(IndexError, d.pop)
        raises(IndexError, d.popleft)
        assert len(d) == 0
        d.append('c')
        assert len(d) == 1
        d.appendleft('d')
        assert len(d) == 2
        d.clear()
        assert len(d) == 0
        assert list(d) == []

    def test_remove(self):
        from _collections import deque
        d = deque('abcdefghcij')
        d.remove('c')
        assert d == deque('abdefghcij')
        d.remove('c')
        assert d == deque('abdefghij')
        raises(ValueError, d.remove, 'c')
        assert d == deque('abdefghij')

    def test_repr(self):
        d = deque(xrange(200))
        e = eval(repr(d))
        self.assertEqual(list(d), list(e))
        d.append(d)
        self.assertIn('...', repr(d))

    def test_print(self):
        d = deque(xrange(200))
        d.append(d)
        test_support.unlink(test_support.TESTFN)
        fo = open(test_support.TESTFN, "wb")
        try:
            print >> fo, d,
            fo.close()
            fo = open(test_support.TESTFN, "rb")
            self.assertEqual(fo.read(), repr(d))
        finally:
            fo.close()
            test_support.unlink(test_support.TESTFN)

    def test_init(self):
        self.assertRaises(TypeError, deque, 'abc', 2, 3);
        self.assertRaises(TypeError, deque, 1);

    def test_hash(self):
        self.assertRaises(TypeError, hash, deque('abc'))

    def test_long_steadystate_queue_popleft(self):
        for size in (0, 1, 2, 100, 1000):
            d = deque(xrange(size))
            append, pop = d.append, d.popleft
            for i in xrange(size, BIG):
                append(i)
                x = pop()
                if x != i - size:
                    self.assertEqual(x, i-size)
            self.assertEqual(list(d), range(BIG-size, BIG))

    def test_long_steadystate_queue_popright(self):
        for size in (0, 1, 2, 100, 1000):
            d = deque(reversed(xrange(size)))
            append, pop = d.appendleft, d.pop
            for i in xrange(size, BIG):
                append(i)
                x = pop()
                if x != i - size:
                    self.assertEqual(x, i-size)
            self.assertEqual(list(reversed(list(d))), range(BIG-size, BIG))

    def test_big_queue_popleft(self):
        pass
        d = deque()
        append, pop = d.append, d.popleft
        for i in xrange(BIG):
            append(i)
        for i in xrange(BIG):
            x = pop()
            if x != i:
                self.assertEqual(x, i)

    def test_big_queue_popright(self):
        d = deque()
        append, pop = d.appendleft, d.pop
        for i in xrange(BIG):
            append(i)
        for i in xrange(BIG):
            x = pop()
            if x != i:
                self.assertEqual(x, i)

    def test_big_stack_right(self):
        d = deque()
        append, pop = d.append, d.pop
        for i in xrange(BIG):
            append(i)
        for i in reversed(xrange(BIG)):
            x = pop()
            if x != i:
                self.assertEqual(x, i)
        self.assertEqual(len(d), 0)

    def test_big_stack_left(self):
        d = deque()
        append, pop = d.appendleft, d.popleft
        for i in xrange(BIG):
            append(i)
        for i in reversed(xrange(BIG)):
            x = pop()
            if x != i:
                self.assertEqual(x, i)
        self.assertEqual(len(d), 0)

    def test_roundtrip_iter_init(self):
        d = deque(xrange(200))
        e = deque(d)
        self.assertNotEqual(id(d), id(e))
        self.assertEqual(list(d), list(e))

    def test_pickle(self):
        d = deque(xrange(200))
        for i in range(pickle.HIGHEST_PROTOCOL + 1):
            s = pickle.dumps(d, i)
            e = pickle.loads(s)
            self.assertNotEqual(id(d), id(e))
            self.assertEqual(list(d), list(e))

##    def test_pickle_recursive(self):
##        d = deque('abc')
##        d.append(d)
##        for i in range(pickle.HIGHEST_PROTOCOL + 1):
##            e = pickle.loads(pickle.dumps(d, i))
##            self.assertNotEqual(id(d), id(e))
##            self.assertEqual(id(e), id(e[-1]))

    def test_deepcopy(self):
        mut = [10]
        d = deque([mut])
        e = copy.deepcopy(d)
        self.assertEqual(list(d), list(e))
        mut[0] = 11
        self.assertNotEqual(id(d), id(e))
        self.assertNotEqual(list(d), list(e))

    def test_copy(self):
        mut = [10]
        d = deque([mut])
        e = copy.copy(d)
        self.assertEqual(list(d), list(e))
        mut[0] = 11
        self.assertNotEqual(id(d), id(e))
        self.assertEqual(list(d), list(e))

    def test_reversed(self):
        for s in ('abcd', xrange(2000)):
            self.assertEqual(list(reversed(deque(s))), list(reversed(s)))

    def test_gc_doesnt_blowup(self):
        import gc
        # This used to assert-fail in deque_traverse() under a debug
        # build, or run wild with a NULL pointer in a release build.
        d = deque()
        for i in xrange(100):
            d.append(1)
            gc.collect()

    def test_container_iterator(self):
        # Bug #3680: tp_traverse was not implemented for deque iterator objects
        class C(object):
            pass
        for i in range(2):
            obj = C()
            ref = weakref.ref(obj)
            if i == 0:
                container = deque([obj, 1])
            else:
                container = reversed(deque([obj, 1]))
            obj.x = iter(container)
            del obj, container
            test_support.gc_collect()
            self.assertTrue(ref() is None, "Cycle was not collected")

class XXXXXXXXXTestVariousIteratorArgs:

    def test_constructor(self):
        for s in ("123", "", range(1000), ('do', 1.2), xrange(2000,2200,5)):
            for g in (seq_tests.Sequence, seq_tests.IterFunc,
                      seq_tests.IterGen, seq_tests.IterFuncStop,
                      seq_tests.itermulti, seq_tests.iterfunc):
                self.assertEqual(list(deque(g(s))), list(g(s)))
            self.assertRaises(TypeError, deque, seq_tests.IterNextOnly(s))
            self.assertRaises(TypeError, deque, seq_tests.IterNoNext(s))
            self.assertRaises(ZeroDivisionError, deque, seq_tests.IterGenExc(s))

    def test_iter_with_altered_data(self):
        d = deque('abcdefg')
        it = iter(d)
        d.pop()
        self.assertRaises(RuntimeError, it.next)

    def test_runtime_error_on_empty_deque(self):
        d = deque()
        it = iter(d)
        d.append(10)
        self.assertRaises(RuntimeError, it.next)

##class Deque(deque):
##    pass

##class DequeWithBadIter(deque):
##    def __iter__(self):
##        raise TypeError

class XXXXXXXXXTestSubclass:

    def test_basics(self):
        d = Deque(xrange(25))
        d.__init__(xrange(200))
        for i in xrange(200, 400):
            d.append(i)
        for i in reversed(xrange(-200, 0)):
            d.appendleft(i)
        self.assertEqual(list(d), range(-200, 400))
        self.assertEqual(len(d), 600)

        left = [d.popleft() for i in xrange(250)]
        self.assertEqual(left, range(-200, 50))
        self.assertEqual(list(d), range(50, 400))

        right = [d.pop() for i in xrange(250)]
        right.reverse()
        self.assertEqual(right, range(150, 400))
        self.assertEqual(list(d), range(50, 150))

        d.clear()
        self.assertEqual(len(d), 0)

    def test_copy_pickle(self):

        d = Deque('abc')

        e = d.__copy__()
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

        e = Deque(d)
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

        s = pickle.dumps(d)
        e = pickle.loads(s)
        self.assertNotEqual(id(d), id(e))
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

        d = Deque('abcde', maxlen=4)

        e = d.__copy__()
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

        e = Deque(d)
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

        s = pickle.dumps(d)
        e = pickle.loads(s)
        self.assertNotEqual(id(d), id(e))
        self.assertEqual(type(d), type(e))
        self.assertEqual(list(d), list(e))

##    def test_pickle(self):
##        d = Deque('abc')
##        d.append(d)
##
##        e = pickle.loads(pickle.dumps(d))
##        self.assertNotEqual(id(d), id(e))
##        self.assertEqual(type(d), type(e))
##        dd = d.pop()
##        ee = e.pop()
##        self.assertEqual(id(e), id(ee))
##        self.assertEqual(d, e)
##
##        d.x = d
##        e = pickle.loads(pickle.dumps(d))
##        self.assertEqual(id(e), id(e.x))
##
##        d = DequeWithBadIter('abc')
##        self.assertRaises(TypeError, pickle.dumps, d)

    def test_weakref(self):
        d = deque('gallahad')
        p = weakref.proxy(d)
        self.assertEqual(str(p), str(d))
        d = None
        test_support.gc_collect()
        self.assertRaises(ReferenceError, str, p)

    def test_strange_subclass(self):
        class X(deque):
            def __iter__(self):
                return iter([])
        d1 = X([1,2,3])
        d2 = X([4,5,6])
        d1 == d2   # not clear if this is supposed to be True or False,
                   # but it used to give a SystemError


##class SubclassWithKwargs(deque):
##    def __init__(self, newarg=1):
##        deque.__init__(self)

class XXXXXXXXXTestSubclassWithKwargs:
    def test_subclass_with_kwargs(self):
        # SF bug #1486663 -- this used to erroneously raise a TypeError
        SubclassWithKwargs(newarg=1)
