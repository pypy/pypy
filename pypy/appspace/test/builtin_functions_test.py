# Python test set -- built-in functions
import autopath
from pypy.interpreter.gateway import app2interp_temp

def app_init_globals():
    ''' support functionality for these tests '''
    import __builtin__ as b

    from sets import Set
    from support_tests import fcmp, have_unicode, TESTFN, unlink

    if not have_unicode:
        b.basestring = str

    import sys, cStringIO

    class Squares:

        def __init__(self, max):
            self.max = max
            self.sofar = []

        def __len__(self): return len(self.sofar)

        def __getitem__(self, i):
            if not 0 <= i < self.max: raise IndexError
            n = len(self.sofar)
            while n <= i:
                self.sofar.append(n*n)
                n += 1
            return self.sofar[i]

    class StrSquares:

        def __init__(self, max):
            self.max = max
            self.sofar = []

        def __len__(self):
            return len(self.sofar)

        def __getitem__(self, i):
            if not 0 <= i < self.max:
                raise IndexError
            n = len(self.sofar)
            while n <= i:
                self.sofar.append(str(n*n))
                n += 1
            return self.sofar[i]

    class BitBucket:
        def write(self, line):
            pass

    L = [
            ('0', 0),
            ('1', 1),
            ('9', 9),
            ('10', 10),
            ('99', 99),
            ('100', 100),
            ('314', 314),
            (' 314', 314),
            ('314 ', 314),
            ('  \t\t  314  \t\t  ', 314),
            (`sys.maxint`, sys.maxint),
            ('  1x', ValueError),
            ('  1  ', 1),
            ('  1\02  ', ValueError),
            ('', ValueError),
            (' ', ValueError),
            ('  \t\t  ', ValueError)
    ]
    if have_unicode:
        L += [
            (unicode('0'), 0),
            (unicode('1'), 1),
            (unicode('9'), 9),
            (unicode('10'), 10),
            (unicode('99'), 99),
            (unicode('100'), 100),
            (unicode('314'), 314),
            (unicode(' 314'), 314),
            (unicode('\u0663\u0661\u0664 ','raw-unicode-escape'), 314),
            (unicode('  \t\t  314  \t\t  '), 314),
            (unicode('  1x'), ValueError),
            (unicode('  1  '), 1),
            (unicode('  1\02  '), ValueError),
            (unicode(''), ValueError),
            (unicode(' '), ValueError),
            (unicode('  \t\t  '), ValueError),
            (unichr(0x200), ValueError),
    ]
    b.Set = Set
    b.fcmp = fcmp
    b.have_unicode = have_unicode
    b.TESTFN = TESTFN
    b.unlink = unlink
    b.sys = sys
    b.cStringIO = cStringIO
    b.Squares = Squares
    b.StrSquares = StrSquares
    b.BitBucket = BitBucket
    b.L = L


class AppTestBuiltin: 
    objspacename = 'std' 

    full_test = 1

    def setup_class(cls): 
        app2interp_temp(app_init_globals)(cls.space)

    # we use "if 1:" to keep all method definitions indented, making
    # it maximally easy to edit this file to pick and choose which
    # ones to run (running everything takes 4 minutes or so...)
    if 1:
        def test_import(self):
            __import__('sys')
            __import__('time')
            __import__('string')
            raises(ImportError, __import__, 'spamspam')
            raises(TypeError, __import__, 1, 2, 3, 4)

        def test_abs(self):
            # int
            assert abs(0) == 0
            assert abs(1234) == 1234
            assert abs(-1234) == 1234
            # float
            assert abs(0.0) == 0.0
            assert abs(3.14) == 3.14
            assert abs(-3.14) == 3.14
            # long
            assert abs(0L) == 0L
            assert abs(1234L) == 1234L
            assert abs(-1234L) == 1234L
            # str
            raises(TypeError, abs, 'a')

        def test_apply(self):
            def f0(*args):
                assert args == ()
            def f1(a1):
                assert a1 == 1
            def f2(a1, a2):
                assert a1 == 1
                assert a2 == 2
            def f3(a1, a2, a3):
                assert a1 == 1
                assert a2 == 2
                assert a3 == 3
            apply(f0, ())
            apply(f1, (1,))
            apply(f2, (1, 2))
            apply(f3, (1, 2, 3))

            # A PyCFunction that takes only positional parameters should allow
            # an empty keyword dictionary to pass without a complaint, but
            # raise a TypeError if the dictionary is non-empty.
            apply(id, (1,), {})
            raises(TypeError, apply, id, (1,), {"foo": 1})
            raises(TypeError, apply)
            raises(TypeError, apply, id, 42)
            raises(TypeError, apply, id, (42,), 42)

        def test_callable(self):
            assert callable(len)
            def f(): pass
            assert callable(f)
            class C:
                def meth(self): pass
            assert callable(C)
            x = C()
            assert callable(x.meth)
            assert not callable(x)
            class D(C):
                def __call__(self): pass
            y = D()
            assert callable(y)
            y()

        def test_chr(self):
            assert chr(32) == ' '
            assert chr(65) == 'A'
            assert chr(97) == 'a'
            assert chr(0xff) == '\xff'
            raises(ValueError, chr, 256)
            raises(TypeError, chr)

        def test_cmp(self):
            assert cmp(-1, 1) == -1
            assert cmp(1, -1) == 1
            assert cmp(1, 1) == 0
            ''' TODO XXX Circular objects not handled yet
            # verify that circular objects are handled
            a = []; a.append(a)
            b = []; b.append(b)
            from UserList import UserList
            c = UserList(); c.append(c)
            assert cmp(a, b) == 0
            assert cmp(b, c) == 0
            assert cmp(c, a) == 0
            assert cmp(a, c) == 0
            # okay, now break the cycles
            a.pop(); b.pop(); c.pop()
            '''
            raises(TypeError, cmp)

        ''' TODO: XXX Coerce is not implemented
        def test_coerce(self):
            assert not fcmp(coerce(1, 1.1), (1.0, 1.1))
            assert coerce(1, 1L) == (1L, 1L)
            assert not fcmp(coerce(1L, 1.1), (1.0, 1.1))
            raises(TypeError, coerce)
            class BadNumber:
                def __coerce__(self, other):
                    raise ValueError
            raises(ValueError, coerce, 42, BadNumber())
            raises(OverflowError, coerce, 0.5, int("12345" * 1000))
        '''

        def test_compile(self):
            compile('print 1\n', '', 'exec')
            bom = '\xef\xbb\xbf'
            compile(bom + 'print 1\n', '', 'exec')
            raises(TypeError, compile)
            raises(ValueError, compile,
                'print 42\n', '<string>', 'badmode')
            raises(ValueError, compile,
                'print 42\n', '<string>', 'single', 0xff)
            if have_unicode:
                compile(unicode('print u"\xc3\xa5"\n', 'utf8'), '', 'exec')

        def test_delattr(self):
            import sys
            sys.spam = 1
            delattr(sys, 'spam')
            raises(TypeError, delattr)

        def test_dir(self):
            x = 1
            assert 'x' in dir()
            import sys
            assert 'modules' in dir(sys)
            raises(TypeError, dir, 42, 42)

        def test_divmod(self):
            assert divmod(12, 7) == (1, 5)
            assert divmod(-12, 7) == (-2, 2)
            assert divmod(12, -7) == (-2, -2)
            assert divmod(-12, -7) == (1, -5)

            assert divmod(12L, 7L) == (1L, 5L)
            assert divmod(-12L, 7L) == (-2L, 2L)
            assert divmod(12L, -7L) == (-2L, -2L)
            assert divmod(-12L, -7L) == (1L, -5L)

            assert divmod(12, 7L) == (1, 5L)
            assert divmod(-12, 7L) == (-2, 2L)
            assert divmod(12L, -7) == (-2L, -2)
            assert divmod(-12L, -7) == (1L, -5)

            assert not fcmp(divmod(3.25, 1.0), (3.0, 0.25))
            assert not fcmp(divmod(-3.25, 1.0), (-4.0, 0.75))
            assert not fcmp(divmod(3.25, -1.0), (-4.0, -0.75))
            assert not fcmp(divmod(-3.25, -1.0), (3.0, -0.25))

            raises(TypeError, divmod)

        ''' XXX TODO No eval() support yet
        def test_eval(self):
            assert eval('1+1') == 2
            assert eval(' 1+1\n') == 2
            globals = {'a': 1, 'b': 2}
            locals = {'b': 200, 'c': 300}
            assert eval('a', globals)  == 1
            assert eval('a', globals, locals) == 1
            assert eval('b', globals, locals) == 200
            assert eval('c', globals, locals) == 300
            if have_unicode:
                assert eval(unicode('1+1')) == 2
                assert eval(unicode(' 1+1\n')) == 2
            globals = {'a': 1, 'b': 2}
            locals = {'b': 200, 'c': 300}
            if have_unicode:
                assert eval(unicode('a'), globals) == 1
                assert eval(unicode('a'), globals, locals) == 1
                assert eval(unicode('b'), globals, locals) == 200
                assert eval(unicode('c'), globals, locals) == 300
                bom = '\xef\xbb\xbf'
                assert eval(bom + 'a', globals, locals) == 1
                assert eval(unicode('u"\xc3\xa5"', 'utf8'), globals) == (
                                 unicode('\xc3\xa5', 'utf8'))
            raises(TypeError, eval)
            raises(TypeError, eval, ())

        '\'' XXX TODO: Figure out later
            # Done outside of the method test_z to get the correct scope
            z = 0
            f = open(TESTFN, 'w')
            f.write('z = z+1\n')
            f.write('z = z*2\n')
            f.close()
            execfile(TESTFN)

        def test_execfile(self):
            globals = {'a': 1, 'b': 2}
            locals = {'b': 200, 'c': 300}

            assert self.__class__.z == 2
            globals['z'] = 0
            execfile(TESTFN, globals)
            assert globals['z'] == 2
            locals['z'] = 0
            execfile(TESTFN, globals, locals)
            assert locals['z'] == 2
            unlink(TESTFN)
            raises(TypeError, execfile)
            import os
            raises(IOError, execfile, os.curdir)
            raises(IOError, execfile, "I_dont_exist")
        '\''
        '''

        ''' XXX TODO: filter does NOT rely on __getitem__, but rather on
            __iter__; it appears to me that the following two tests,
            therefore, pass in CPython only because of the accident that
            in that implementation str does not define __iter__ (while
            list and tuple do, in 2.3).  Probably best to substitute
            most of these tests with more appropriate ones!
        '''
        def test_filter(self):
            assert filter(lambda c: 'a' <= c <= 'z', 'Hello World') == (
                'elloorld')
            assert (filter(None, [1, 'hello', [], [3], '', None, 9, 0])
                ) == [1, 'hello', [3], 9]
            assert filter(lambda x: x > 0, [1, -3, 9, 0, 2]) == (
                [1, 9, 2])
            assert filter(None, Squares(10)) == (
                [1, 4, 9, 16, 25, 36, 49, 64, 81])
            assert filter(lambda x: x%2, Squares(10)) == (
                [1, 9, 25, 49, 81])
            def identity(item):
                return 1
            filter(identity, Squares(5))
            raises(TypeError, filter)
            ''' XXX rest of test disabled as above explained
            class BadSeq(object):
                def __getitem__(self, index):
                    if index<4:
                        return 42
                    raise ValueError
            raises(ValueError, filter, lambda x: x, BadSeq())
            def badfunc():
                pass
            raises(TypeError, filter, badfunc, range(5))

            # test bltinmodule.c::filtertuple()
            assert filter(None, (1, 2)) == (1, 2)
            assert filter(lambda x: x>=3, (1, 2, 3, 4)) == (3, 4)
            raises(TypeError, filter, 42, (1, 2))

            # test bltinmodule.c::filterstring()
            assert filter(None, "12") == "12"
            assert filter(lambda x: x>="3", "1234") == "34"
            raises(TypeError, filter, 42, "12")
            class badstr(str):
                def __getitem__(self, index):
                    raise ValueError
            raises(ValueError, filter,
                lambda x: x >="3", badstr("1234"))

            class badstr2(str):
                def __getitem__(self, index):
                    return 42
            raises(TypeError, filter,
                lambda x: x >=42, badstr2("1234"))

            class weirdstr(str):
                def __getitem__(self, index):
                    return weirdstr(2*str.__getitem__(self, index))
            assert filter(lambda x: x>="33", weirdstr("1234")) == (
                "3344")

            class shiftstr(str):
                def __getitem__(self, index):
                    return chr(ord(str.__getitem__(self, index))+1)
            assert filter(lambda x: x>="3", shiftstr("1234")) == "345"

            if have_unicode:
                # test bltinmodule.c::filterunicode()
                assert filter(None, unicode("12")) == unicode("12")
                assert filter(lambda x: x>="3", unicode("1234")) == (
                    unicode("34"))
                raises(TypeError, filter, 42, unicode("12"))
                raises(ValueError, filter, lambda x: x >="3",
                    badstr(unicode("1234")))

                class badunicode(unicode):
                    def __getitem__(self, index):
                        return 42
                raises(TypeError, filter, lambda x: x >=42,
                    badunicode("1234"))

                class weirdunicode(unicode):
                    def __getitem__(self, index):
                        return weirdunicode(2*unicode.__getitem__(self, index))
                assert (
                    filter(lambda x: x>=unicode("33"), weirdunicode("1234"))) == (
                        unicode("3344"))

                class shiftunicode(unicode):
                    def __getitem__(self, index):
                        return unichr(ord(unicode.__getitem__(self, index))+1)
                assert (
                    filter(lambda x: x>=unicode("3"), shiftunicode("1234"))) == (
                    unicode("345")
                )

        def test_filter_subclasses(self):
            # test that filter() never returns tuple, str or unicode subclasses
            # and that the result always goes through __getitem__
            funcs = (None, bool, lambda x: True)
            class tuple2(tuple):
                def __getitem__(self, index):
                    return 2*tuple.__getitem__(self, index)
            class str2(str):
                def __getitem__(self, index):
                    return 2*str.__getitem__(self, index)
            inputs = {
                tuple2: {(): (), (1, 2, 3): (2, 4, 6)},
                str2:   {"": "", "123": "112233"}
            }
            if have_unicode:
                class unicode2(unicode):
                    def __getitem__(self, index):
                        return 2*unicode.__getitem__(self, index)
                inputs[unicode2] = {
                    unicode(): unicode(),
                    unicode("123"): unicode("112233")
                }

            for (cls, inps) in inputs.iteritems():
                for (inp, exp) in inps.iteritems():
                    # make sure the output goes through __getitem__
                    # even if func is None
                    assert (
                        filter(funcs[0], cls(inp))) == (
                        filter(funcs[1], cls(inp))
                    )
                    for func in funcs:
                        outp = filter(func, cls(inp))
                        assert outp == exp
                        assert not isinstance(outp, cls)
        '''

        def test_float(self):
            assert float(3.14) == 3.14
            assert float(314) == 314.0
            assert float(314L) == 314.0
            assert float("  3.14  ") == 3.14
            if have_unicode:
                assert float(unicode("  3.14  ")) == 3.14
                assert float(unicode(
                    "  \u0663.\u0661\u0664  ",'raw-unicode-escape')) == 3.14

        def test_getattr(self):
            import sys
            assert getattr(sys, 'stdout') is sys.stdout
            raises(TypeError, getattr, sys, 1)
            raises(TypeError, getattr, sys, 1, "foo")
            raises(TypeError, getattr)
            if have_unicode:
                raises(UnicodeError, getattr, sys,
                    unichr(sys.maxunicode))

        def test_hasattr(self):
            import sys
            assert hasattr(sys, 'stdout')
            raises(TypeError, hasattr, sys, 1)
            raises(TypeError, hasattr)
            if have_unicode:
                 raises(UnicodeError, hasattr, sys,
                     unichr(sys.maxunicode))

        def test_hash(self):
            hash(None)
            assert hash(1) == hash(1L)
            assert hash(1) == hash(1.0)
            hash('spam')
            if have_unicode:
                assert hash('spam') == hash(unicode('spam'))
            hash((0,1,2,3))
            def f(): pass
            raises(TypeError, hash, [])
            raises(TypeError, hash, {})

        def test_hex(self):
            assert hex(16) == '0x10'
            assert hex(16L) == '0x10L'
            assert len(hex(-1)) == len(hex(sys.maxint))
            assert hex(-16) in ('0xfffffff0', '0xfffffffffffffff0')
            assert hex(-16L) == '-0x10L'
            raises(TypeError, hex, {})

        def test_id(self):
            id(None)
            id(1)
            id(1L)
            id(1.0)
            id('spam')
            id((0,1,2,3))
            id([0,1,2,3])
            id({'spam': 1, 'eggs': 2, 'ham': 3})

        # Test input() later, together with raw_input

        def test_int(self):
            assert int(314) == 314
            assert int(3.14) == 3
            assert int(314L) == 314
            # Check that conversion from float truncates towards zero
            assert int(-3.14) == -3
            assert int(3.9) == 3
            assert int(-3.9) == -3
            assert int(3.5) == 3
            assert int(-3.5) == -3
            # Different base:
            assert int("10",16) == 16L
            if have_unicode:
                assert int(unicode("10"),16) == 16L
            # Test conversion from strings and various anomalies
            for s, v in L:
                for sign in "", "+", "-":
                    for prefix in "", " ", "\t", "  \t\t  ":
                        ss = prefix + sign + s
                        vv = v
                        if sign == "-" and v is not ValueError:
                            vv = -v
                        try:
                            assert int(ss) == vv
                        except v:
                            pass

            s = `-1-sys.maxint`
            assert int(s)+1 == -sys.maxint
            # should return long
            ''' XXX TODO:  Longs not well supported yet
            int(s[1:])

            # should return long
            x = int(1e100)
            assert isinstance(x, long)
            x = int(-1e100)
            assert isinstance(x, long)
            '''

            # SF bug 434186:  0x80000000/2 != 0x80000000>>1.
            # Worked by accident in Windows release build, but failed in
            # debug build.  Failed in all Linux builds.
            x = -1-sys.maxint
            assert x >> 1 == x//2

            raises(ValueError, int, '123\0')
            raises(ValueError, int, '53', 40)

            ''' XXX TODO:  Longs not supported yet
            x = int('1' * 600)
            assert isinstance(x, long)

            if have_unicode:
                x = int(unichr(0x661) * 600)
                assert isinstance(x, long)

            raises(TypeError, int, 1, 12)
            '''

            assert int('0123', 0) == 83

        def test_intern(self):
            raises(TypeError, intern)
            s = "never interned before"
            assert intern(s) is s
            s2 = s.swapcase().swapcase()
            assert intern(s2) is s

        def test_iter(self):
            raises(TypeError, iter)
            raises(TypeError, iter, 42, 42)
            lists = [("1", "2"), ["1", "2"], "12"]
            if have_unicode:
                lists.append(unicode("12"))
            for l in lists:
                i = iter(l)
                assert i.next() == '1'
                assert i.next() == '2'
                raises(StopIteration, i.next)

        def test_isinstance(self):
            class C:
                pass
            class D(C):
                pass
            class E:
                pass
            c = C()
            d = D()
            e = E()
            assert isinstance(c, C)
            assert isinstance(d, C)
            assert not isinstance(e, C)
            assert not isinstance(c, D)
            assert not isinstance('foo', E)
            raises(TypeError, isinstance, E, 'foo')
            raises(TypeError, isinstance)

        def test_issubclass(self):
            class C:
                pass
            class D(C):
                pass
            class E:
                pass
            c = C()
            d = D()
            e = E()
            assert issubclass(D, C)
            assert issubclass(C, C)
            assert not issubclass(C, D)
            raises(TypeError, issubclass, 'foo', E)
            raises(TypeError, issubclass, E, 'foo')
            raises(TypeError, issubclass)

        def test_len(self):
            assert len('123') == 3
            assert len(()) == 0
            assert len((1, 2, 3, 4)) == 4
            assert len([1, 2, 3, 4]) == 4
            assert len({}) == 0
            assert len({'a':1, 'b': 2}) == 2
            class BadSeq:
                def __len__(self):
                    raise ValueError
            raises(ValueError, len, BadSeq())

    if 1:

        def test_list(self):
            assert list([]) == []
            l0_3 = [0, 1, 2, 3]
            l0_3_bis = list(l0_3)
            assert l0_3 == l0_3_bis
            assert l0_3 is not l0_3_bis
            assert list(()) == []
            assert list((0, 1, 2, 3)) == [0, 1, 2, 3]
            assert list('') == []
            assert list('spam') == ['s', 'p', 'a', 'm']

            ''' XXX TODO: disabled for now -- far too slow!
            if sys.maxint == 0x7fffffff:
                # This test can currently only work on 32-bit machines.
                # XXX If/when PySequence_Length() returns a ssize_t, it should be
                # XXX re-enabled.
                # Verify clearing of bug #556025.
                # This assumes that the max data size (sys.maxint) == max
                # address size this also assumes that the address size is at
                # least 4 bytes with 8 byte addresses, the bug is not well
                # tested
                #
                # Note: This test is expected to SEGV under Cygwin 1.3.12 or
                # earlier due to a newlib bug.  See the following mailing list
                # thread for the details:

                #     http://sources.redhat.com/ml/newlib/2002/msg00369.html
                raises(MemoryError, list, xrange(sys.maxint // 2))
            '''

        ''' XXX TODO: disabled for now -- long not yet well supported
        def test_long(self):
            assert long(314) == 314L
            assert long(3.14) == 3L
            assert long(314L) == 314L
            # Check that conversion from float truncates towards zero
            assert long(-3.14) == -3L
            assert long(3.9) == 3L
            assert long(-3.9) == -3L
            assert long(3.5) == 3L
            assert long(-3.5) == -3L
            assert long("-3") == -3L
            if have_unicode:
                assert long(unicode("-3")) == -3L
            # Different base:
            assert long("10",16) == 16L
            if have_unicode:
                assert long(unicode("10"),16) == 16L
            # Check conversions from string (same test set as for int(), and then some)
            LL = [
                    ('1' + '0'*20, 10L**20),
                    ('1' + '0'*100, 10L**100)
            ]
            L2 = L[:]
            if have_unicode:
                L2 += [
                    (unicode('1') + unicode('0')*20, 10L**20),
                    (unicode('1') + unicode('0')*100, 10L**100),
            ]
            for s, v in L2 + LL:
                for sign in "", "+", "-":
                    for prefix in "", " ", "\t", "  \t\t  ":
                        ss = prefix + sign + s
                        vv = v
                        if sign == "-" and v is not ValueError:
                            vv = -v
                        try:
                            assert long(ss) == long(vv)
                        except v:
                            pass

            raises(ValueError, long, '123\0')
            raises(ValueError, long, '53', 40)
            raises(TypeError, long, 1, 12)
        '''

        def test_map(self):
            assert (
                map(None, 'hello world')) == (
                ['h','e','l','l','o',' ','w','o','r','l','d']
            )
            assert (
                map(None, 'abcd', 'efg')) == (
                [('a', 'e'), ('b', 'f'), ('c', 'g'), ('d', None)]
            )
            assert (
                map(None, range(10))) == (
                [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
            )
            assert (
                map(lambda x: x*x, range(1,4))) == (
                [1, 4, 9]
            )
            try:
                from math import sqrt
            except ImportError:
                def sqrt(x):
                    return pow(x, 0.5)
            assert (
                map(lambda x: map(sqrt,x), [[16, 4], [81, 9]])) == (
                [[4.0, 2.0], [9.0, 3.0]]
            )
            assert (
                map(lambda x, y: x+y, [1,3,2], [9,1,4])) == (
                [10, 4, 6]
            )

            def plus(*v):
                accu = 0
                for i in v: accu = accu + i
                return accu
            assert (
                map(plus, [1, 3, 7])) == (
                [1, 3, 7]
            )
            assert (
                map(plus, [1, 3, 7], [4, 9, 2])) == (
                [1+4, 3+9, 7+2]
            )
            assert (
                map(plus, [1, 3, 7], [4, 9, 2], [1, 1, 0])) == (
                [1+4+1, 3+9+1, 7+2+0]
            )
            assert (
                map(None, Squares(10))) == (
                [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
            )
            assert (
                map(int, Squares(10))) == (
                [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
            )
            assert (
                map(None, Squares(3), Squares(2))) == (
                [(0,0), (1,1), (4,None)]
            )
            assert (
                map(max, Squares(3), Squares(2))) == (
                [0, 1, 4]
            )
            raises(TypeError, map)
            raises(TypeError, map, lambda x: x, 42)
            assert map(None, [42]) == [42]
            class BadSeq:
                def __getitem__(self, index):
                    raise ValueError
            raises(ValueError, map, lambda x: x, BadSeq())

        def test_max(self):
            assert max('123123') == '3'
            assert max(1, 2, 3) == 3
            assert max((1, 2, 3, 1, 2, 3)) == 3
            assert max([1, 2, 3, 1, 2, 3]) == 3

            assert max(1, 2L, 3.0) == 3.0
            assert max(1L, 2.0, 3) == 3
            assert max(1.0, 2, 3L) == 3L

        def test_min(self):
            assert min('123123') == '1'
            assert min(1, 2, 3) == 1
            assert min((1, 2, 3, 1, 2, 3)) == 1
            assert min([1, 2, 3, 1, 2, 3]) == 1

            assert min(1, 2L, 3.0) == 1
            assert min(1L, 2.0, 3) == 1L
            assert min(1.0, 2, 3L) == 1.0

            raises(TypeError, min)
            raises(TypeError, min, 42)
            raises(ValueError, min, ())
            class BadSeq:
                def __getitem__(self, index):
                    raise ValueError
            raises(ValueError, min, BadSeq())
            ''' XXX TODO: some weird bug in pypy here -- fix later
            class BadNumber:
                def __cmp__(self, other):
                    raise ValueError
            raises(ValueError, min, (42, BadNumber()))
            '''

        def test_oct(self):
            assert oct(100) == '0144'
            assert oct(100L) == '0144L'
            assert oct(-100) in ('037777777634', '01777777777777777777634')
            assert oct(-100L) == '-0144L'
            raises(TypeError, oct, ())


        def test_open(self):
            def write_testfile():
                # NB the first 4 lines are also used to test input and raw_input, below
                fp = open(TESTFN, 'w')
                try:
                    fp.write('1+1\n')
                    fp.write('1+1\n')
                    fp.write('The quick brown fox jumps over the lazy dog')
                    fp.write('.\n')
                    fp.write('Dear John\n')
                    fp.write('XXX'*100)
                    fp.write('YYY'*100)
                finally:
                    fp.close()
            write_testfile()
            fp = open(TESTFN, 'r')
            try:
                assert fp.readline(4) == '1+1\n'
                assert fp.readline(4) == '1+1\n'
                assert fp.readline() == 'The quick brown fox jumps over the lazy dog.\n'
                assert fp.readline(4) == 'Dear'
                assert fp.readline(100) == ' John\n'
                assert fp.read(300) == 'XXX'*100
                assert fp.read(1000) == 'YYY'*100
            finally:
                fp.close()
            unlink(TESTFN)

        def test_ord(self):
            assert ord(' ') == 32
            assert ord('A') == 65
            assert ord('a') == 97
            raises(TypeError, ord, 42)
            if have_unicode:
                assert ord(unichr(sys.maxunicode)) == sys.maxunicode
                raises(TypeError, ord, unicode("12"))

        def test_pow(self):
            assert pow(0,0) == 1
            assert pow(0,1) == 0
            assert pow(1,0) == 1
            assert pow(1,1) == 1

            assert pow(2,0) == 1
            assert pow(2,10) == 1024
            assert pow(2,20) == 1024*1024
            assert pow(2,30) == 1024*1024*1024

            assert pow(-2,0) == 1
            assert pow(-2,1) == -2
            assert pow(-2,2) == 4
            assert pow(-2,3) == -8

            assert pow(0L,0) == 1
            assert pow(0L,1) == 0
            assert pow(1L,0) == 1
            assert pow(1L,1) == 1

            assert pow(2L,0) == 1
            assert pow(2L,10) == 1024
            assert pow(2L,20) == 1024*1024
            assert pow(2L,30) == 1024*1024*1024

            assert pow(-2L,0) == 1
            assert pow(-2L,1) == -2
            assert pow(-2L,2) == 4
            assert pow(-2L,3) == -8

            assert round(pow(0.,0) - 1., 7) == 0
            assert round(pow(0.,1) - 0., 7) == 0
            assert round(pow(1.,0) - 1., 7) == 0
            assert round(pow(1.,1) - 1., 7) == 0

            assert round(pow(2.,0) - 1., 7) == 0
            assert round(pow(2.,10) - 1024., 7) == 0
            assert round(pow(2.,20) - 1024.*1024., 7) == 0
            assert round(pow(2.,30) - 1024.*1024.*1024., 7) == 0

            assert round(pow(-2.,0) - 1., 7) == 0
            assert round(pow(-2.,1) - -2., 7) == 0
            assert round(pow(-2.,2) - 4., 7) == 0
            assert round(pow(-2.,3) - -8., 7) == 0

            for x in 2, 2L, 2.0:
                for y in 10, 10L, 10.0:
                    for z in 1000, 1000L, 1000.0:
                        if isinstance(x, float) or \
                           isinstance(y, float) or \
                           isinstance(z, float):
                            raises(TypeError, pow, x, y, z)
                        else:
                            assert round(pow(x, y, z) - 24.0, 7) == 0

            raises(TypeError, pow, -1, -2, 3)
            raises(ValueError, pow, 1, 2, 0)
            raises(TypeError, pow, -1L, -2L, 3L)
            raises(ValueError, pow, 1L, 2L, 0L)
            raises(ValueError, pow, -342.43, 0.234)

            raises(TypeError, pow)

        def test_range(self):
            assert range(3) == [0, 1, 2]
            assert range(1, 5) == [1, 2, 3, 4]
            assert range(0) == []
            assert range(-3) == []
            assert range(1, 10, 3) == [1, 4, 7]
            assert range(5, -5, -3) == [5, 2, -1, -4]

            # Now test range() with longs
            assert range(-2**100) == []
            assert range(0, -2**100) == []
            assert range(0, 2**100, -1) == []
            assert range(0, 2**100, -1) == []

            a = long(10 * sys.maxint)
            b = long(100 * sys.maxint)
            c = long(50 * sys.maxint)

            assert range(a, a+2) == [a, a+1]
            assert range(a+2, a, -1L) == [a+2, a+1]
            assert range(a+4, a, -2) == [a+4, a+2]

            seq = range(a, b, c)
            assert a in seq
            assert b not in seq
            assert len(seq) == 2

            seq = range(b, a, -c)
            assert b in seq
            assert a not in seq
            assert len(seq) == 2

            seq = range(-a, -b, -c)
            assert -a in seq
            assert -b not in seq
            assert len(seq) == 2

            raises(TypeError, range)
            raises(TypeError, range, 1, 2, 3, 4)
            raises(ValueError, range, 1, 2, 0)

            # Reject floats when it would require PyLongs to represent.
            # (smaller floats still accepted, but deprecated)
            raises(TypeError, range, 1e100, 1e101, 1e101)

            raises(TypeError, range, 0, "spam")
            raises(TypeError, range, 0, 42, "spam")

            raises(OverflowError, range, -sys.maxint, sys.maxint)
            raises(OverflowError, range, 0, 2*sys.maxint)

        ''' XXX TODO: input and raw_input not supported yet
        def test_input_and_raw_input(self):
            self.write_testfile()
            fp = open(TESTFN, 'r')
            savestdin = sys.stdin
            savestdout = sys.stdout # Eats the echo
            try:
                sys.stdin = fp
                sys.stdout = BitBucket()
                assert input() == 2
                assert input('testing\n') == 2
                assert raw_input() == 'The quick brown fox jumps over the lazy dog.'
                assert raw_input('testing\n') == 'Dear John'
                sys.stdin = cStringIO.StringIO("NULL\0")
                raises(TypeError, input, 42, 42)
                sys.stdin = cStringIO.StringIO("    'whitespace'")
                assert input() == 'whitespace'
                sys.stdin = cStringIO.StringIO()
                raises(EOFError, input)
                del sys.stdout
                raises(RuntimeError, input, 'prompt')
                del sys.stdin
                raises(RuntimeError, input, 'prompt')
            finally:
                sys.stdin = savestdin
                sys.stdout = savestdout
                fp.close()
                unlink(TESTFN)
        '''

        def test_reduce(self):
            assert reduce(lambda x, y: x+y, ['a', 'b', 'c'], '') == 'abc'
            assert (
                reduce(lambda x, y: x+y, [['a', 'c'], [], ['d', 'w']], [])) == (
                ['a','c','d','w']
            )
            assert reduce(lambda x, y: x*y, range(2,8), 1) == 5040
            assert (
                reduce(lambda x, y: x*y, range(2,21), 1L)) == (
                2432902008176640000L
            )
            assert reduce(lambda x, y: x+y, Squares(10)) == 285
            assert reduce(lambda x, y: x+y, Squares(10), 0) == 285
            assert reduce(lambda x, y: x+y, Squares(0), 0) == 0
            raises(TypeError, reduce)
            raises(TypeError, reduce, 42, 42)
            raises(TypeError, reduce, 42, 42, 42)
            assert reduce(42, "1") == "1" # func is never called with one item
            assert reduce(42, "", "1") == "1" # func is never called with one item
            raises(TypeError, reduce, 42, (42, 42))

            class BadSeq:
                def __getitem__(self, index):
                    raise ValueError
            raises(ValueError, reduce, 42, BadSeq())

        ''' XXX TODO: we don't have reload yet
        def test_reload(self):
            import sys
            reload(sys)
            import string
            reload(string)
            ## import sys
            ## raises(ImportError, reload, sys)
        '''

        def test_repr(self):
            assert repr('') == '\'\''
            assert repr(0) == '0'
            assert repr(0L) == '0L'
            assert repr(()) == '()'
            assert repr([]) == '[]'
            assert repr({}) == '{}'
            ''' XXX TODO: we don't yet support "circular" objects!
            a = []
            a.append(a)
            assert repr(a) == '[[...]]'
            a = {}
            a[0] = a
            assert repr(a) == '{0: {...}}'
            '''

        def test_round(self):
            assert round(0.0) == 0.0
            assert round(1.0) == 1.0
            assert round(10.0) == 10.0
            assert round(1000000000.0) == 1000000000.0
            assert round(1e20) == 1e20

            assert round(-1.0) == -1.0
            assert round(-10.0) == -10.0
            assert round(-1000000000.0) == -1000000000.0
            assert round(-1e20) == -1e20

            assert round(0.1) == 0.0
            assert round(1.1) == 1.0
            assert round(10.1) == 10.0
            assert round(1000000000.1) == 1000000000.0

            assert round(-1.1) == -1.0
            assert round(-10.1) == -10.0
            assert round(-1000000000.1) == -1000000000.0

            assert round(0.9) == 1.0
            assert round(9.9) == 10.0
            assert round(999999999.9) == 1000000000.0

            assert round(-0.9) == -1.0
            assert round(-9.9) == -10.0
            assert round(-999999999.9) == -1000000000.0

            assert round(-8.0, -1) == -10.0

            raises(TypeError, round)

        def test_setattr(self):
            setattr(sys, 'spam', 1)
            assert sys.spam == 1
            raises(TypeError, setattr, sys, 1, 'spam')
            raises(TypeError, setattr)

        def test_str(self):
            assert str('') == ''
            assert str(0) == '0'
            assert str(0L) == '0'
            assert str(()) == '()'
            assert str([]) == '[]'
            assert str({}) == '{}'
            ''' XXX TODO: we don't yet support "circular" objects!
            a = []
            a.append(a)
            assert str(a) == '[[...]]'
            a = {}
            a[0] = a
            assert str(a) == '{0: {...}}'
            '''

        def test_sum(self):
            assert sum([]) == 0
            assert sum(range(2,8)) == 27
            assert sum(iter(range(2,8))) == 27
            assert sum(Squares(10)) == 285
            assert sum(iter(Squares(10))) == 285
            assert sum([[1], [2], [3]], []) == [1, 2, 3]

            raises(TypeError, sum)
            raises(TypeError, sum, 42)
            raises(TypeError, sum, ['a', 'b', 'c'])
            raises(TypeError, sum, ['a', 'b', 'c'], '')
            raises(TypeError, sum, [[1], [2], [3]])
            raises(TypeError, sum, [{2:3}])
            raises(TypeError, sum, [{2:3}]*2, {2:3})

            class BadSeq:
                def __getitem__(self, index):
                    raise ValueError
            raises(ValueError, sum, BadSeq())

        def test_tuple(self):
            assert tuple(()) == ()
            t0_3 = (0, 1, 2, 3)
            t0_3_bis = tuple(t0_3)
            ''' XXX TODO: tuples are immutable -- returns same object in CPython '''
            #self.assert_(t0_3 is t0_3_bis)
            assert t0_3 == t0_3_bis
            assert tuple([]) == ()
            assert tuple([0, 1, 2, 3]) == (0, 1, 2, 3)
            assert tuple('') == ()
            assert tuple('spam') == ('s', 'p', 'a', 'm')

        def test_type(self):
            assert type('') ==  type('123')
            assert type('') != type(())

        def test_unichr(self):
            if have_unicode:
                assert unichr(32) == unicode(' ')
                assert unichr(65) == unicode('A')
                assert unichr(97) == unicode('a')
                assert (
                    unichr(sys.maxunicode)) == (
                    unicode('\\U%08x' % (sys.maxunicode), 'unicode-escape')
                )
                raises(ValueError, unichr, sys.maxunicode+1)
                raises(TypeError, unichr)

        def test_vars(self):
            def get_vars_f0():
                return vars()
            def get_vars_f2():
                get_vars_f0()
                a = 1
                b = 2
                return vars()
            assert Set(vars()) == Set(dir())
            import sys
            assert Set(vars(sys)) == Set(dir(sys))
            assert get_vars_f0() == {}
            assert get_vars_f2() == {'a': 1, 'b': 2}
            raises(TypeError, vars, 42, 42)
            raises(TypeError, vars, 42)

        def test_zip(self):
            a = (1, 2, 3)
            b = (4, 5, 6)
            t = [(1, 4), (2, 5), (3, 6)]
            assert zip(a, b) == t
            b = [4, 5, 6]
            assert zip(a, b) == t
            b = (4, 5, 6, 7)
            assert zip(a, b) == t
            class I:
                def __getitem__(self, i):
                    if i < 0 or i > 2: raise IndexError
                    return i + 4
            assert zip(a, I()) == t
            raises(TypeError, zip)
            raises(TypeError, zip, None)
            class G:
                pass
            raises(TypeError, zip, a, G())

            # Make sure zip doesn't try to allocate a billion elements for the
            # result list when one of its arguments doesn't say how long it is.
            # A MemoryError is the most likely failure mode.
            class SequenceWithoutALength:
                def __getitem__(self, i):
                    if i == 5:
                        raise IndexError
                    else:
                        return i
            s = SequenceWithoutALength()
            assert (
                zip(s, xrange(2**30))) == (
                [(x,x) for x in s]
            )

            class BadSeq:
                def __getitem__(self, i):
                    if i == 5:
                        raise ValueError
                    else:
                        return i
            raises(ValueError, zip, BadSeq(), BadSeq())
