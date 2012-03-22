import py
from pypy.conftest import gettestobjspace


class AppTestItertools: 
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['itertools'])

    def test_count(self):
        import itertools

        it = itertools.count()
        for x in range(10):
            assert next(it) == x

    def test_count_firstval(self):
        import itertools

        it = itertools.count(3)
        for x in range(10):
            assert next(it) == x + 3

    def test_count_repr(self):
        import itertools

        it = itertools.count(123)
        assert repr(it) == 'count(123)'
        next(it)
        assert repr(it) == 'count(124)'
        it = itertools.count(12.1, 1.0)
        assert repr(it) == 'count(12.1, 1.0)'

    def test_count_invalid(self):
        import itertools

        raises(TypeError, itertools.count, None)
        raises(TypeError, itertools.count, 'a')

    def test_repeat(self):
        import itertools

        o = object()
        it = itertools.repeat(o)

        for x in range(10):
            assert o is next(it)

    def test_repeat_times(self):
        import itertools

        times = 10
        it = itertools.repeat(None, times)
        for i in range(times):
            next(it)
        raises(StopIteration, next, it)

        #---does not work in CPython 2.5
        #it = itertools.repeat(None, None)
        #for x in range(10):
        #    it.next()    # Should be no StopIteration

        it = itertools.repeat(None, 0)
        raises(StopIteration, next, it)
        raises(StopIteration, next, it)

        it = itertools.repeat(None, -1)
        raises(StopIteration, next, it)
        raises(StopIteration, next, it)

    def test_repeat_overflow(self):
        import itertools
        import sys

        raises(OverflowError, itertools.repeat, None, sys.maxint + 1)

    def test_repeat_repr(self):
        import itertools

        it = itertools.repeat('foobar')
        assert repr(it) == "repeat('foobar')"
        next(it)
        assert repr(it) == "repeat('foobar')"

        it = itertools.repeat('foobar', 10)
        assert repr(it) == "repeat('foobar', 10)"
        next(it)
        assert repr(it) == "repeat('foobar', 9)"
        list(it)
        assert repr(it) == "repeat('foobar', 0)"

    def test_takewhile(self):
        import itertools

        it = itertools.takewhile(bool, [])
        raises(StopIteration, next, it)

        it = itertools.takewhile(bool, [False, True, True])
        raises(StopIteration, next, it)

        it = itertools.takewhile(bool, [1, 2, 3, 0, 1, 1])
        for x in [1, 2, 3]:
            assert next(it) == x

        raises(StopIteration, next, it)

    def test_takewhile_wrongargs(self):
        import itertools

        it = itertools.takewhile(None, [1])
        raises(TypeError, next, it)

        raises(TypeError, itertools.takewhile, bool, None)

    def test_dropwhile(self):
        import itertools

        it = itertools.dropwhile(bool, [])
        raises(StopIteration, next, it)

        it = itertools.dropwhile(bool, [True, True, True])
        raises(StopIteration, next, it)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.dropwhile(is_odd, [1, 3, 5, 2, 4, 6])
        for x in [2, 4, 6]:
            assert next(it) == x

        raises(StopIteration, next, it)

    def test_dropwhile_wrongargs(self):
        import itertools

        it = itertools.dropwhile(None, [1])
        raises(TypeError, next, it)

        raises(TypeError, itertools.dropwhile, bool, None)

    def test_ifilter(self):
        import itertools

        it = itertools.ifilter(None, [])
        raises(StopIteration, next, it)

        it = itertools.ifilter(None, [1, 0, 2, 3, 0])
        for x in [1, 2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.ifilter(is_odd, [1, 2, 3, 4, 5, 6])
        for x in [1, 3, 5]:
            assert next(it) == x
        raises(StopIteration, next, it)

    def test_ifilter_wrongargs(self):
        import itertools

        it = itertools.ifilter(0, [1])
        raises(TypeError, next, it)

        raises(TypeError, itertools.ifilter, bool, None)

    def test_ifilterfalse(self):
        import itertools

        it = itertools.ifilterfalse(None, [])
        raises(StopIteration, next, it)

        it = itertools.ifilterfalse(None, [1, 0, 2, 3, 0])
        for x in [0, 0]:
            assert next(it) == x
        raises(StopIteration, next, it)

        def is_odd(arg):
            return (arg % 2 == 1)

        it = itertools.ifilterfalse(is_odd, [1, 2, 3, 4, 5, 6])
        for x in [2, 4, 6]:
            assert next(it) == x
        raises(StopIteration, next, it)

    def test_ifilterfalse_wrongargs(self):
        import itertools

        it = itertools.ifilterfalse(0, [1])
        raises(TypeError, next, it)

        raises(TypeError, itertools.ifilterfalse, bool, None)

    def test_islice(self):
        import itertools

        it = itertools.islice([], 0)
        raises(StopIteration, next, it)

        it = itertools.islice([1, 2, 3], 0)
        raises(StopIteration, next, it)

        it = itertools.islice([1, 2, 3, 4, 5], 3)
        for x in [1, 2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        it = itertools.islice([1, 2, 3, 4, 5], 1, 3)
        for x in [2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        it = itertools.islice([1, 2, 3, 4, 5], 0, 3, 2)
        for x in [1, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        it = itertools.islice([1, 2, 3], 0, None)
        for x in [1, 2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        assert list(itertools.islice(range(100), 10, 3)) == []

        # new in 2.5: start=None or step=None
        assert list(itertools.islice(range(10), None)) == list(range(10))
        assert list(itertools.islice(range(10), None,None)) == list(range(10))
        assert list(itertools.islice(range(10), None,None,None)) == list(range(10))

    def test_islice_dropitems_exact(self):
        import itertools

        it = iter("abcdefghij")
        itertools.islice(it, 2, 2)    # doesn't eagerly drop anything
        assert next(it) == "a"
        itertools.islice(it, 3, 8, 2)    # doesn't eagerly drop anything
        assert next(it) == "b"
        assert next(it) == "c"

        it = iter("abcdefghij")
        x = next(itertools.islice(it, 2, 3), None)    # drops 2 items
        assert x == "c"
        assert next(it) == "d"

        it = iter("abcdefghij")
        x = next(itertools.islice(it, 3, 8, 2), None)    # drops 3 items
        assert x == "d"
        assert next(it) == "e"

        it = iter("abcdefghij")
        x = next(itertools.islice(it, None, 8), None)    # drops 0 items
        assert x == "a"
        assert next(it) == "b"

        it = iter("abcdefghij")
        x = next(itertools.islice(it, 3, 2), None)    # drops 3 items
        assert x is None
        assert next(it) == "d"

        it = iter("abcdefghij")
        islc = itertools.islice(it, 3, 7, 2)
        assert next(islc) == "d"    # drops 0, 1, 2, returns item #3
        assert next(it) == "e"
        assert next(islc) == "g"    # drops the 4th and return item #5
        assert next(it) == "h"
        raises(StopIteration, next, islc)  # drops the 6th and raise
        assert next(it) == "j"

        it = iter("abcdefghij")
        islc = itertools.islice(it, 3, 4, 3)
        assert next(islc) == "d"    # drops 0, 1, 2, returns item #3
        assert next(it) == "e"
        raises(StopIteration, next, islc)  # item #4 is 'stop', so just raise
        assert next(it) == "f"

    def test_islice_overflow(self):
        import itertools
        import sys
        raises((OverflowError, ValueError),    # ValueError on top of CPython
               itertools.islice, [], sys.maxint + 1)

    def test_islice_wrongargs(self):
        import itertools

        raises(TypeError, itertools.islice, None, 0)

        raises(ValueError, itertools.islice, [], -1)

        raises(ValueError, itertools.islice, [], -1, 0)
        raises(ValueError, itertools.islice, [], 0, -1)

        raises(ValueError, itertools.islice, [], 0, 0, -1)
        raises(ValueError, itertools.islice, [], 0, 0, 0)

        raises(TypeError, itertools.islice, [], 0, 0, 0, 0)

    def test_chain(self):
        import itertools
        
        it = itertools.chain()
        raises(StopIteration, next, it)
        raises(StopIteration, next, it)
        
        it = itertools.chain([1, 2, 3])
        for x in [1, 2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

        it = itertools.chain([1, 2, 3], [4], [5, 6])
        for x in [1, 2, 3, 4, 5, 6]:
            assert next(it) == x
        raises(StopIteration, next, it)

        it = itertools.chain([], [], [1], [])
        assert next(it) == 1
        raises(StopIteration, next, it)

    def test_imap(self):
        import itertools

        obj_list = [object(), object(), object()]
        it = itertools.imap(None, obj_list)
        for x in obj_list:
            assert next(it) == (x, )
        raises(StopIteration, next, it)

        it = itertools.imap(None, [1, 2, 3], [4], [5, 6])
        assert next(it) == (1, 4, 5)
        raises(StopIteration, next, it)

        it = itertools.imap(None, [], [], [1], [])
        raises(StopIteration, next, it)

        it = itertools.imap(str, [0, 1, 0, 1])
        for x in ['0', '1', '0', '1']:
            assert next(it) == x
        raises(StopIteration, next, it)

        import operator
        it = itertools.imap(operator.add, [1, 2, 3], [4, 5, 6])
        for x in [5, 7, 9]:
            assert next(it) == x
        raises(StopIteration, next, it)

    def test_imap_wrongargs(self):
        import itertools
        
        # Duplicate python 2.4 behaviour for invalid arguments
        it = itertools.imap(0, [])
        raises(StopIteration, next, it)
        it = itertools.imap(0, [0])
        raises(TypeError, next, it)
        raises(TypeError, itertools.imap, None, 0)

        raises(TypeError, itertools.imap, None)
        raises(TypeError, itertools.imap, bool)
        raises(TypeError, itertools.imap, 42)

    def test_cycle(self):
        import itertools

        it = itertools.cycle([])
        raises(StopIteration, next, it)
        
        it = itertools.cycle([1, 2, 3])
        for x in [1, 2, 3, 1, 2, 3, 1, 2, 3]:
            assert next(it) == x

    def test_starmap(self):
        import itertools, operator

        it = itertools.starmap(operator.add, [])
        raises(StopIteration, next, it)

        it = itertools.starmap(operator.add, [(0, 1), (2, 3), (4, 5)])
        for x in [1, 5, 9]:
            assert next(it) == x
        raises(StopIteration, next, it)

        assert list(itertools.starmap(operator.add, [iter((40,2))])) == [42]

    def test_starmap_wrongargs(self):
        import itertools

        it = itertools.starmap(None, [(1, )])
        raises(TypeError, next, it)

        it = itertools.starmap(None, [])
        raises(StopIteration, next, it)

        it = itertools.starmap(bool, [0])
        raises(TypeError, next, it)

    def test_tee(self):
        import itertools

        it1, it2 = itertools.tee([])
        raises(StopIteration, next, it1)
        raises(StopIteration, next, it2)

        it1, it2 = itertools.tee([1, 2, 3])
        for x in [1, 2]:
            assert next(it1) == x
        for x in [1, 2, 3]:
            assert next(it2) == x
        assert next(it1) == 3
        raises(StopIteration, next, it1)
        raises(StopIteration, next, it2)

        assert itertools.tee([], 0) == ()

        iterators = itertools.tee([1, 2, 3], 10)
        for it in iterators:
            for x in [1, 2, 3]:
                assert next(it) == x
            raises(StopIteration, next, it)

    def test_tee_wrongargs(self):
        import itertools
        
        raises(TypeError, itertools.tee, 0)
        raises(ValueError, itertools.tee, [], -1)
        raises(TypeError, itertools.tee, [], None)

    def test_tee_optimization(self):
        import itertools

        a, b = itertools.tee(iter('foobar'))
        c, d = itertools.tee(b)
        assert c is b
        assert a is not c
        assert a is not d
        assert c is not d
        res = list(a)
        assert res == list('foobar')
        res = list(c)
        assert res == list('foobar')
        res = list(d)
        assert res == list('foobar')

    def test_tee_instantiate(self):
        import itertools

        a, b = itertools.tee(iter('foobar'))
        c = type(a)(a)
        assert a is not b
        assert a is not c
        assert b is not c
        res = list(a)
        assert res == list('foobar')
        res = list(b)
        assert res == list('foobar')
        res = list(c)
        assert res == list('foobar')

    def test_groupby(self):
        import itertools
        
        it = itertools.groupby([])
        raises(StopIteration, next, it)

        it = itertools.groupby([1, 2, 2, 3, 3, 3, 4, 4, 4, 4])
        for x in [1, 2, 3, 4]:
            k, g = next(it)
            assert k == x
            assert len(list(g)) == x
            raises(StopIteration, next, g)
        raises(StopIteration, next ,it)

        it = itertools.groupby([0, 1, 2, 3, 4, 5], None)
        for x in [0, 1, 2, 3, 4, 5]:
            k, g = next(it)
            assert k == x
            assert next(g) == x
            raises(StopIteration, next, g)
        raises(StopIteration, next, it)

        # consumes after group started
        it = itertools.groupby([0, 0, 0, 0, 1])
        k1, g1 = next(it)
        assert next(g1) == 0
        k2, g2 = next(it)
        raises(StopIteration, next, g1)
        assert next(g2) == 1
        raises(StopIteration, next, g2)

        # skips with not started group
        it = itertools.groupby([0, 0, 1])
        k1, g1 = next(it)
        k2, g2 = next(it)
        raises(StopIteration, next, g1)
        assert next(g2) == 1
        raises(StopIteration, next, g2)

        it = itertools.groupby([0, 1, 2])
        k1, g1 = next(it)
        k2, g2 = next(it)
        k2, g3 = next(it)
        raises(StopIteration, next, g1)
        raises(StopIteration, next, g2)
        assert next(g3) == 2

        def half_floor(x):
            return x // 2
        it = itertools.groupby([0, 1, 2, 3, 4, 5], half_floor)
        for x in [0, 1, 2]:
            k, g = next(it)
            assert k == x
            assert half_floor(next(g)) == x
            assert half_floor(next(g)) == x
            raises(StopIteration, next, g)
        raises(StopIteration, next, it)

        # keyword argument
        it = itertools.groupby([0, 1, 2, 3, 4, 5], key = half_floor)
        for x in [0, 1, 2]:
            k, g = next(it)
            assert k == x
            assert list(g) == [x*2, x*2+1]
        raises(StopIteration, next, it)

        # Grouping is not based on key identity
        class NeverEqual(object):
            def __eq__(self, other):
                return False
        objects = [NeverEqual(), NeverEqual(), NeverEqual()]
        it = itertools.groupby(objects)
        for x in objects:
            print("Trying", x)
            k, g = next(it)
            assert k is x
            assert next(g) is x
            raises(StopIteration, next, g)
        raises(StopIteration, next, it)
        
        # Grouping is based on key equality
        class AlwaysEqual(object):
            def __eq__(self, other):
                return True
        objects = [AlwaysEqual(), AlwaysEqual(), AlwaysEqual()]
        it = itertools.groupby(objects)
        k, g = next(it)
        assert k is objects[0]
        for x in objects:
            assert next(g) is x
        raises(StopIteration, next, g)
        raises(StopIteration, next, it)

    def test_groupby_wrongargs(self):
        import itertools

        raises(TypeError, itertools.groupby, 0)
        it = itertools.groupby([0], 1)
        raises(TypeError, next, it)

    def test_iterables(self):
        import itertools
    
        iterables = [
            itertools.chain(),
            itertools.count(),
            itertools.cycle([]),
            itertools.dropwhile(bool, []),
            itertools.groupby([]),
            itertools.ifilter(None, []),
            itertools.ifilterfalse(None, []),
            itertools.imap(None, []),
            itertools.islice([], 0),
            itertools.repeat(None),
            itertools.starmap(bool, []),
            itertools.takewhile(bool, []),
            itertools.tee([])[0],
            itertools.tee([])[1],
            ]
    
        for it in iterables:
            assert hasattr(it, '__iter__')
            assert iter(it) is it
            assert hasattr(it, '__next__')
            assert callable(it.__next__)

    def test_docstrings(self):
        import itertools
        
        assert itertools.__doc__
        methods = [
            itertools.chain,
            itertools.count,
            itertools.cycle,
            itertools.dropwhile,
            itertools.groupby,
            itertools.ifilter,
            itertools.ifilterfalse,
            itertools.imap,
            itertools.islice,
            itertools.repeat,
            itertools.starmap,
            itertools.takewhile,
            itertools.tee,
            ]
        for method in methods:
            assert method.__doc__

    def test_tee_weakrefable(self):
        import itertools, weakref

        a, b = itertools.tee(iter('abc'))
        ref = weakref.ref(b)
        assert ref() is b


class AppTestItertools26:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['itertools'])
        if cls.space.is_true(cls.space.appexec([], """():
            import sys; return sys.version_info < (2, 6)
            """)):
            py.test.skip("Requires Python 2.6")

    def test_count_overflow(self):
        import itertools, sys
        it = itertools.count(sys.maxint - 1)
        assert next(it) == sys.maxint - 1
        assert next(it) == sys.maxint
        assert next(it) == sys.maxint + 1
        it = itertools.count(sys.maxint + 1)
        assert next(it) == sys.maxint + 1
        assert next(it) == sys.maxint + 2
        it = itertools.count(-sys.maxint-2)
        assert next(it) == -sys.maxint - 2
        assert next(it) == -sys.maxint - 1
        assert next(it) == -sys.maxint
        assert next(it) == -sys.maxint + 1
        it = itertools.count(0, sys.maxint)
        assert next(it) == sys.maxint * 0
        assert next(it) == sys.maxint * 1
        assert next(it) == sys.maxint * 2
        it = itertools.count(0, sys.maxint + 1)
        assert next(it) == (sys.maxint + 1) * 0
        assert next(it) == (sys.maxint + 1) * 1
        assert next(it) == (sys.maxint + 1) * 2

    def test_chain_fromiterable(self):
        import itertools
        l = [[1, 2, 3], [4], [5, 6]]
        it = itertools.chain.from_iterable(l)
        assert list(it) == sum(l, [])

    def test_combinations(self):
        from itertools import combinations

        raises(TypeError, combinations, "abc")
        raises(TypeError, combinations, "abc", 2, 1)
        raises(TypeError, combinations, None)
        raises(ValueError, combinations, "abc", -2)
        assert list(combinations(range(4), 3)) == [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]

    def test_ziplongest(self):
        from itertools import zip_longest, islice, count
        for args in [
                ['abc', range(6)],
                [range(6), 'abc'],
                [range(100), range(200,210), range(300,305)],
                [range(100), range(0), range(300,305), range(120), range(150)],
                [range(100), range(0), range(300,305), range(120), range(0)],
            ]:
            # target = map(None, *args) <- this raises a py3k warning
            # this is the replacement:
            target = [tuple([arg[i] if i < len(arg) else None for arg in args])
                      for i in range(max(map(len, args)))]
            assert list(zip_longest(*args)) == target
            assert list(zip_longest(*args, **{})) == target

            # Replace None fills with 'X'
            target = [tuple((e is None and 'X' or e) for e in t) for t in target]
            assert list(zip_longest(*args, **dict(fillvalue='X'))) ==  target

        # take 3 from infinite input
        assert (list(islice(zip_longest('abcdef', count()),3)) ==
                zip('abcdef', range(3)))

        assert list(zip_longest()) == zip()
        assert list(zip_longest([])) ==  zip([])
        assert list(zip_longest('abcdef')) ==  zip('abcdef')

        assert (list(zip_longest('abc', 'defg', **{})) ==
                zip(list('abc') + [None], 'defg'))  # empty keyword dict
        raises(TypeError, zip_longest, 3)
        raises(TypeError, zip_longest, range(3), 3)

        for stmt in [
            "zip_longest('abc', fv=1)",
            "zip_longest('abc', fillvalue=1, bogus_keyword=None)",
        ]:
            try:
                eval(stmt, globals(), locals())
            except TypeError:
                pass
            else:
                self.fail('Did not raise Type in:  ' + stmt)

    def test_zip_longest2(self):
        import itertools
        class Repeater(object):
            # this class is similar to itertools.repeat
            def __init__(self, o, t, e):
                self.o = o
                self.t = int(t)
                self.e = e
            def __iter__(self): # its iterator is itself
                return self
            def __next__(self):
                if self.t > 0:
                    self.t -= 1
                    return self.o
                else:
                    raise self.e

        # Formerly this code in would fail in debug mode
        # with Undetected Error and Stop Iteration
        r1 = Repeater(1, 3, StopIteration)
        r2 = Repeater(2, 4, StopIteration)
        def run(r1, r2):
            result = []
            for i, j in itertools.zip_longest(r1, r2, fillvalue=0):
                result.append((i, j))
            return result
        assert run(r1, r2) ==  [(1,2), (1,2), (1,2), (0,2)]

    def test_product(self):
        from itertools import product
        l = [1, 2]
        m = ['a', 'b']

        prodlist = product(l, m)
        res = [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]
        assert list(prodlist) == res
        assert list(product()) == [()]
        assert list(product([])) == []
        assert list(product(iter(l), iter(m))) == res

        prodlist = product(iter(l), iter(m))
        assert list(prodlist) == [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]

    def test_product_repeat(self):
        from itertools import product
        l = [1, 2]
        m = ['a', 'b']

        prodlist = product(l, m, repeat=2)
        ans = [(1, 'a', 1, 'a'), (1, 'a', 1, 'b'), (1, 'a', 2, 'a'),
               (1, 'a', 2, 'b'), (1, 'b', 1, 'a'), (1, 'b', 1, 'b'),
               (1, 'b', 2, 'a'), (1, 'b', 2, 'b'), (2, 'a', 1, 'a'),
               (2, 'a', 1, 'b'), (2, 'a', 2, 'a'), (2, 'a', 2, 'b'),
               (2, 'b', 1, 'a'), (2, 'b', 1, 'b'), (2, 'b', 2, 'a'),
               (2, 'b', 2, 'b')]
        assert list(prodlist) == ans

        raises(TypeError, product, [], foobar=3)

    def test_product_diff_sizes(self):
        from itertools import product
        l = [1, 2]
        m = ['a']

        prodlist = product(l, m)
        assert list(prodlist) == [(1, 'a'), (2, 'a')]

        l = [1]
        m = ['a', 'b']
        prodlist = product(l, m)
        assert list(prodlist) == [(1, 'a'), (1, 'b')]

        assert list(product([], [1, 2, 3])) == []
        assert list(product([1, 2, 3], [])) == []

    def test_product_toomany_args(self):
        from itertools import product
        l = [1, 2]
        m = ['a']
        raises(TypeError, product, l, m, repeat=1, foo=2)

    def test_product_empty(self):
        from itertools import product
        prod = product('abc', repeat=0)
        assert next(prod) == ()
        raises (StopIteration, next, prod)

    def test_permutations(self):
        from itertools import permutations
        assert list(permutations('AB')) == [('A', 'B'), ('B', 'A')]
        assert list(permutations('ABCD', 2)) == [
            ('A', 'B'),
            ('A', 'C'),
            ('A', 'D'),
            ('B', 'A'),
            ('B', 'C'),
            ('B', 'D'),
            ('C', 'A'),
            ('C', 'B'),
            ('C', 'D'),
            ('D', 'A'),
            ('D', 'B'),
            ('D', 'C'),
            ]
        assert list(permutations(range(3))) == [
            (0, 1, 2),
            (0, 2, 1),
            (1, 0, 2),
            (1, 2, 0),
            (2, 0, 1),
            (2, 1, 0),
            ]
        assert list(permutations([])) == [()]
        assert list(permutations([], 0)) == [()]
        assert list(permutations([], 1)) == []
        assert list(permutations(range(3), 4)) == []
        #
        perm = list(permutations([1, 2, 3, 4]))
        assert perm == [(1, 2, 3, 4), (1, 2, 4, 3), (1, 3, 2, 4), (1, 3, 4, 2),
                        (1, 4, 2, 3), (1, 4, 3, 2), (2, 1, 3, 4), (2, 1, 4, 3),
                        (2, 3, 1, 4), (2, 3, 4, 1), (2, 4, 1, 3), (2, 4, 3, 1),
                        (3, 1, 2, 4), (3, 1, 4, 2), (3, 2, 1, 4), (3, 2, 4, 1),
                        (3, 4, 1, 2), (3, 4, 2, 1), (4, 1, 2, 3), (4, 1, 3, 2),
                        (4, 2, 1, 3), (4, 2, 3, 1), (4, 3, 1, 2), (4, 3, 2, 1)]

    def test_permutations_r(self):
        from itertools import permutations
        perm = list(permutations([1, 2, 3, 4], 2))
        assert perm == [(1, 2), (1, 3), (1, 4), (2, 1), (2, 3), (2, 4), (3, 1),
                       (3, 2), (3, 4), (4, 1), (4, 2), (4, 3)]

    def test_permutations_r_gt_n(self):
        from itertools import permutations
        perm = permutations([1, 2], 3)
        raises(StopIteration, next, perm)

    def test_permutations_neg_r(self):
        from itertools import permutations
        raises(ValueError, permutations, [1, 2], -1)


class AppTestItertools27:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['itertools', 'struct'])
        if cls.space.is_true(cls.space.appexec([], """():
            import sys; return sys.version_info < (2, 7)
            """)):
            py.test.skip("Requires Python 2.7")

    def test_compress(self):
        import itertools
        it = itertools.compress(['a', 'b', 'c'], [0, 1, 0])
        assert list(it) == ['b']

    def test_compress_diff_len(self):
        import itertools
        it = itertools.compress(['a'], [])
        raises(StopIteration, next, it)

    def test_count_kwargs(self):
        import itertools
        it = itertools.count(start=2, step=3)
        assert next(it) == 2
        assert next(it) == 5
        assert next(it) == 8

    def test_repeat_kwargs(self):
        import itertools
        assert list(itertools.repeat(object='a', times=3)) == ['a', 'a', 'a']

    def test_combinations_overflow(self):
        from itertools import combinations
        assert list(combinations("abc", 32)) == []

    def test_combinations_with_replacement(self):
        from itertools import combinations_with_replacement
        raises(TypeError, combinations_with_replacement, "abc")
        raises(TypeError, combinations_with_replacement, "abc", 2, 1)
        raises(TypeError, combinations_with_replacement, None)
        raises(ValueError, combinations_with_replacement, "abc", -2)
        assert list(combinations_with_replacement("ABC", 2)) == [("A", "A"), ("A", 'B'), ("A", "C"), ("B", "B"), ("B", "C"), ("C", "C")]

    def test_combinations_with_replacement_shortcases(self):
        from itertools import combinations_with_replacement
        assert list(combinations_with_replacement([-12], 2)) == [(-12, -12)]
        assert list(combinations_with_replacement("AB", 3)) == [
            ("A", "A", "A"), ("A", "A", "B"),
            ("A", "B", "B"), ("B", "B", "B")]
        assert list(combinations_with_replacement([], 2)) == []
        assert list(combinations_with_replacement([], 0)) == [()]

    def test_zip_longest3(self):
        import itertools
        class Repeater(object):
            # this class is similar to itertools.repeat
            def __init__(self, o, t, e):
                self.o = o
                self.t = int(t)
                self.e = e
            def __iter__(self): # its iterator is itself
                return self
            def __next__(self):
                if self.t > 0:
                    self.t -= 1
                    return self.o
                else:
                    raise self.e

        # Formerly, the RuntimeError would be lost
        # and StopIteration would stop as expected
        r1 = Repeater(1, 3, RuntimeError)
        r2 = Repeater(2, 4, StopIteration)
        it = itertools.zip_longest(r1, r2, fillvalue=0)
        assert next(it) == (1, 2)
        assert next(it) == (1, 2)
        assert next(it)== (1, 2)
        raises(RuntimeError, next, it)

    def test_subclassing(self):
        import itertools
        class A(itertools.count): pass
        assert type(A(5)) is A
        class A(itertools.repeat): pass
        assert type(A('foo')) is A
        class A(itertools.takewhile): pass
        assert type(A(lambda x: True, [])) is A
        class A(itertools.dropwhile): pass
        assert type(A(lambda x: True, [])) is A
        class A(itertools.ifilter): pass
        assert type(A(lambda x: True, [])) is A
        class A(itertools.ifilterfalse): pass
        assert type(A(lambda x: True, [])) is A
        class A(itertools.islice): pass
        assert type(A([], 0)) is A
        class A(itertools.chain): pass
        assert type(A([], [])) is A
        assert type(A.from_iterable([])) is A
        class A(itertools.imap): pass
        assert type(A(lambda: 5, [])) is A
        class A(itertools.zip_longest): pass
        assert type(A([], [])) is A
        class A(itertools.cycle): pass
        assert type(A([])) is A
        class A(itertools.starmap): pass
        assert type(A(lambda: 5, [])) is A
        class A(itertools.groupby): pass
        assert type(A([], lambda: 5)) is A
        class A(itertools.compress): pass
        assert type(A('', [])) is A
        class A(itertools.product): pass
        assert type(A('', '')) is A
        class A(itertools.combinations): pass
        assert type(A('', 0)) is A
        class A(itertools.combinations_with_replacement): pass
        assert type(A('', 0)) is A

    def test_copy_pickle(self):
        import itertools, copy, pickle, sys
        for value in [42, -sys.maxint*99]:
            for step in [1, sys.maxint*42, 5.5]:
                expected = [value, value+step, value+2*step]
                c = itertools.count(value, step)
                assert list(itertools.islice(c, 3)) == expected
                c = itertools.count(value, step)
                c1 = copy.copy(c)
                assert list(itertools.islice(c1, 3)) == expected
                c2 = copy.deepcopy(c)
                assert list(itertools.islice(c2, 3)) == expected
                c3 = pickle.loads(pickle.dumps(c))
                assert list(itertools.islice(c3, 3)) == expected
