

class Test_DescrOperation:

    def test_nonzero(self):
        space = self.space
        assert space.nonzero(space.w_True) is space.w_True
        assert space.nonzero(space.w_False) is space.w_False
        assert space.nonzero(space.wrap(42)) is space.w_True
        assert space.nonzero(space.wrap(0)) is space.w_False
        l = space.newlist([])
        assert space.nonzero(l) is space.w_False
        space.call_method(l, 'append', space.w_False)
        assert space.nonzero(l) is space.w_True

    def test_isinstance_and_issubtype_ignore_special(self):
        space = self.space
        w_tup = space.appexec((), """():
        class Meta(type):
            def __subclasscheck__(mcls, cls):
                return False
        class Base:
            __metaclass__ = Meta
        class Sub(Base):
            pass
        return Base, Sub""")
        w_base, w_sub = space.unpackiterable(w_tup)
        assert space.is_true(space.issubtype(w_sub, w_base))
        w_inst = space.call_function(w_sub)
        assert space.isinstance_w(w_inst, w_base)


class AppTest_Descroperation:
    OPTIONS = {}

    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**cls.OPTIONS)

    def test_special_methods(self):
        class OldStyle:
            pass
        for base in (object, OldStyle,):
            class A(base):
                def __lt__(self, other):
                    return "lt"
                def __imul__(self, other):
                    return "imul"
                def __sub__(self, other):
                    return "sub"
                def __rsub__(self, other):
                    return "rsub"
                def __pow__(self, other):
                    return "pow"
                def __rpow__(self, other):
                    return "rpow"
                def __neg__(self):
                    return "neg"
            a = A()
            assert (a < 5) == "lt"
            assert (object() > a) == "lt"
            a1 = a
            a1 *= 4
            assert a1 == "imul"
            assert a - 2 == "sub"
            assert a - object() == "sub"
            assert 2 - a == "rsub"
            assert object() - a == "rsub"
            assert a ** 2 == "pow"
            assert a ** object() == "pow"
            assert 2 ** a == "rpow"
            assert object() ** a == "rpow"
            assert -a == "neg"

            class B(A):
                def __lt__(self, other):
                    return "B's lt"
                def __imul__(self, other):
                    return "B's imul"
                def __sub__(self, other):
                    return "B's sub"
                def __rsub__(self, other):
                    return "B's rsub"
                def __pow__(self, other):
                    return "B's pow"
                def __rpow__(self, other):
                    return "B's rpow"
                def __neg__(self):
                    return "B's neg"

            b = B()
            assert (a < b) == "lt"
            assert (b > a) == "lt"
            b1 = b
            b1 *= a
            assert b1 == "B's imul"
            a1 = a
            a1 *= b
            assert a1 == "imul"

            if base is object:
                assert a - b == "B's rsub"
            else:
                assert a - b == "sub"
            assert b - a == "B's sub"
            assert b - b == "B's sub"
            if base is object:
                assert a ** b == "B's rpow"
            else:
                assert a ** b == "pow"
            assert b ** a == "B's pow"
            assert b ** b == "B's pow"
            assert -b == "B's neg"

            class C(B):
                pass
            c = C()
            assert c - 1 == "B's sub"
            assert 1 - c == "B's rsub"
            assert c - b == "B's sub"
            assert b - c == "B's sub"

            assert c ** 1 == "B's pow"
            assert 1 ** c == "B's rpow"
            assert c ** b == "B's pow"
            assert b ** c == "B's pow"

    def test_getslice(self):
        class Sq(object):
            def __getslice__(self, start, stop):
                return (start, stop)
            def __getitem__(self, key):
                return "booh"
            def __len__(self):
                return 100

        sq = Sq()

        assert sq[1:3] == (1,3)
        slice_min, slice_max = sq[:]
        assert slice_min == 0
        assert slice_max >= 2**31-1
        assert sq[1:] == (1, slice_max)
        assert sq[:3] == (0, 3)
        assert sq[:] == (0, slice_max)
        # negative indices
        assert sq[-1:3] == (99, 3)
        assert sq[1:-3] == (1, 97)
        assert sq[-1:-3] == (99, 97)
        # extended slice syntax always uses __getitem__()
        assert sq[::] == "booh"

    def test_setslice(self):
        class Sq(object):
            def __setslice__(self, start, stop, sequence):
                ops.append((start, stop, sequence))
            def __setitem__(self, key, value):
                raise AssertionError, key
            def __len__(self):
                return 100

        sq = Sq()
        ops = []
        sq[-5:3] = 'hello'
        sq[12:] = 'world'
        sq[:-1] = 'spam'
        sq[:] = 'egg'
        slice_max = ops[-1][1]
        assert slice_max >= 2**31-1

        assert ops == [
            (95, 3,          'hello'),
            (12, slice_max, 'world'),
            (0,  99,         'spam'),
            (0,  slice_max, 'egg'),
            ]

    def test_delslice(self):
        class Sq(object):
            def __delslice__(self, start, stop):
                ops.append((start, stop))
            def __delitem__(self, key):
                raise AssertionError, key
            def __len__(self):
                return 100

        sq = Sq()
        ops = []
        del sq[5:-3]
        del sq[-12:]
        del sq[:1]
        del sq[:]
        slice_max = ops[-1][1]
        assert slice_max >= 2**31-1

        assert ops == [
            (5,   97),
            (88,  slice_max),
            (0,   1),
            (0,   slice_max),
            ]

    def test_getslice_nolength(self):
        class Sq(object):
            def __getslice__(self, start, stop):
                return (start, stop)
            def __getitem__(self, key):
                return "booh"

        sq = Sq()

        assert sq[1:3] == (1,3)
        slice_min, slice_max = sq[:]
        assert slice_min == 0
        assert slice_max >= 2**31-1
        assert sq[1:] == (1, slice_max)
        assert sq[:3] == (0, 3)
        assert sq[:] == (0, slice_max)
        # negative indices, but no __len__
        assert sq[-1:3] == (-1, 3)
        assert sq[1:-3] == (1, -3)
        assert sq[-1:-3] == (-1, -3)
        # extended slice syntax always uses __getitem__()
        assert sq[::] == "booh"

    def test_ipow(self):
        x = 2
        x **= 5
        assert x == 32

    def test_typechecks(self):
        class myint(int):
            pass
        class X(object):
            def __nonzero__(self):
                return myint(1)
        raises(TypeError, "not X()")

    def test_string_subclass(self):
        class S(str):
            def __hash__(self):
                return 123
        s = S("abc")
        setattr(s, s, s)
        assert len(s.__dict__) == 1
        # this behavior changed in 2.4
        #assert type(s.__dict__.keys()[0]) is str   # don't store S keys
        #assert s.abc is s
        assert getattr(s,s) is s

    def test_notimplemented(self):
        #import types
        import operator

        def specialmethod(self, other):
            return NotImplemented

        def check(expr, x, y, operator=operator):
            raises(TypeError, expr)

        for metaclass in [type]:   # [type, types.ClassType]:
            for name, expr, iexpr in [
                    ('__add__',      'x + y',                   'x += y'),
                    ('__sub__',      'x - y',                   'x -= y'),
                    ('__mul__',      'x * y',                   'x *= y'),
                    ('__truediv__',  'operator.truediv(x, y)',  None),
                    ('__floordiv__', 'operator.floordiv(x, y)', None),
                    ('__div__',      'x / y',                   'x /= y'),
                    ('__mod__',      'x % y',                   'x %= y'),
                    ('__divmod__',   'divmod(x, y)',            None),
                    ('__pow__',      'x ** y',                  'x **= y'),
                    ('__lshift__',   'x << y',                  'x <<= y'),
                    ('__rshift__',   'x >> y',                  'x >>= y'),
                    ('__and__',      'x & y',                   'x &= y'),
                    ('__or__',       'x | y',                   'x |= y'),
                    ('__xor__',      'x ^ y',                   'x ^= y'),
                    ('__coerce__',   'coerce(x, y)',            None)]:
                if name == '__coerce__':
                    rname = name
                else:
                    rname = '__r' + name[2:]
                A = metaclass('A', (), {name: specialmethod})
                B = metaclass('B', (), {rname: specialmethod})
                a = A()
                b = B()
                check(expr, a, a)
                check(expr, a, b)
                check(expr, b, a)
                check(expr, b, b)
                check(expr, a, 5)
                check(expr, 5, b)
                if iexpr:
                    check(iexpr, a, a)
                    check(iexpr, a, b)
                    check(iexpr, b, a)
                    check(iexpr, b, b)
                    check(iexpr, a, 5)
                    iname = '__i' + name[2:]
                    C = metaclass('C', (), {iname: specialmethod})
                    c = C()
                    check(iexpr, c, a)
                    check(iexpr, c, b)
                    check(iexpr, c, 5)

    def test_string_results(self):
        class A(object):
            def __str__(self):
                return answer * 2
            def __repr__(self):
                return answer * 3
            def __hex__(self):
                return answer * 4
            def __oct__(self):
                return answer * 5

        for operate, n in [(str, 2), (repr, 3), (hex, 4), (oct, 5)]:
            answer = "hello"
            assert operate(A()) == "hello" * n
            if operate not in (hex, oct):
                answer = u"world"
                assert operate(A()) == "world" * n
            assert type(operate(A())) is str
            answer = 42
            raises(TypeError, operate, A())

    def test_missing_getattribute(self):
        class X(object): pass

        class Y(X):
          class __metaclass__(type):
            def mro(cls):
              return [cls, X]

        x = X()
        x.__class__ = Y
        raises(AttributeError, getattr, x, 'a')

    def test_silly_but_consistent_order(self):
        # incomparable objects sort by type name :-/
        class A(object): pass
        class zz(object): pass
        assert A() < zz()
        assert zz() > A()
        # if in doubt, CPython sorts numbers before non-numbers
        assert 0 < ()
        assert 0L < ()
        assert 0.0 < ()
        assert 0j < ()
        assert 0 < []
        assert 0L < []
        assert 0.0 < []
        assert 0j < []
        assert 0 < A()
        assert 0L < A()
        assert 0.0 < A()
        assert 0j < A()
        assert 0 < zz()
        assert 0L < zz()
        assert 0.0 < zz()
        assert 0j < zz()
        # what if the type name is the same... whatever, but
        # be consistent
        a1 = A()
        a2 = A()
        class A(object): pass
        a3 = A()
        a4 = A()
        assert (a1 < a3) == (a1 < a4) == (a2 < a3) == (a2 < a4)

    def test_setattrweakref(self):
        skip("fails, works in cpython")
        # The issue is that in CPython, none of the built-in types have
        # a __weakref__ descriptor, even if their instances are weakrefable.
        # Should we emulate this?
        class P(object):
            pass

        setattr(P, "__weakref__", 0)

    def test_subclass_addition(self):
        # the __radd__ is never called (compare with the next test)
        l = []
        class A(object):
            def __add__(self, other):
                l.append(self.__class__)
                l.append(other.__class__)
                return 123
            def __radd__(self, other):
                # should never be called!
                return 456
        class B(A):
            pass
        res1 = A() + B()
        res2 = B() + A()
        assert res1 == res2 == 123
        assert l == [A, B, B, A]

    def test_subclass_comparison(self):
        # the __eq__ *is* called with reversed arguments
        l = []
        class A(object):
            def __eq__(self, other):
                l.append(self.__class__)
                l.append(other.__class__)
                return False

            def __lt__(self, other):
                l.append(self.__class__)
                l.append(other.__class__)
                return False

        class B(A):
            pass

        A() == B()
        A() < B()
        B() < A()
        assert l == [B, A, A, B, B, A]

    def test_subclass_comparison_more(self):
        # similarly, __gt__(b,a) is called instead of __lt__(a,b)
        l = []
        class A(object):
            def __lt__(self, other):
                l.append(self.__class__)
                l.append(other.__class__)
                return '<'
            def __gt__(self, other):
                l.append(self.__class__)
                l.append(other.__class__)
                return '>'
        class B(A):
            pass
        res1 = A() < B()
        res2 = B() < A()
        assert res1 == '>' and res2 == '<'
        assert l == [B, A, B, A]

    def test_rich_comparison(self):
        # Old-style
        class A:
            def __init__(self, a):
                self.a = a
            def __eq__(self, other):
                return self.a == other.a
        class B:
            def __init__(self, a):
                self.a = a
        # New-style
        class C(object):
            def __init__(self, a):
                self.a = a
            def __eq__(self, other):
                return self.a == other.a
        class D(object):
            def __init__(self, a):
                self.a = a

        assert A(1) == B(1)
        assert B(1) == A(1)
        assert A(1) == C(1)
        assert C(1) == A(1)
        assert A(1) == D(1)
        assert D(1) == A(1)
        assert C(1) == D(1)
        assert D(1) == C(1)
        assert not(A(1) == B(2))
        assert not(B(1) == A(2))
        assert not(A(1) == C(2))
        assert not(C(1) == A(2))
        assert not(A(1) == D(2))
        assert not(D(1) == A(2))
        assert not(C(1) == D(2))
        assert not(D(1) == C(2))

    def test_eq_order(self):
        class A(object):
            def __eq__(self, other): return True
            def __ne__(self, other): return True
            def __lt__(self, other): return True
            def __le__(self, other): return True
            def __gt__(self, other): return True
            def __ge__(self, other): return True
        class B(object):
            def __eq__(self, other): return False
            def __ne__(self, other): return False
            def __lt__(self, other): return False
            def __le__(self, other): return False
            def __gt__(self, other): return False
            def __ge__(self, other): return False
        #
        assert A() == B()
        assert A() != B()
        assert A() <  B()
        assert A() <= B()
        assert A() >  B()
        assert A() >= B()
        #
        assert not (B() == A())
        assert not (B() != A())
        assert not (B() <  A())
        assert not (B() <= A())
        assert not (B() >  A())
        assert not (B() >= A())
        #
        class C(A):
            def __eq__(self, other): return False
            def __ne__(self, other): return False
            def __lt__(self, other): return False
            def __le__(self, other): return False
            def __gt__(self, other): return False
            def __ge__(self, other): return False
        #
        assert not (A() == C())
        assert not (A() != C())
        assert not (A() <  C())
        assert not (A() <= C())
        assert not (A() >  C())
        assert not (A() >= C())
        #
        assert not (C() == A())
        assert not (C() != A())
        assert not (C() <  A())
        assert not (C() <= A())
        assert not (C() >  A())
        assert not (C() >= A())

    def test_addition(self):
        # Old-style
        class A:
            def __init__(self, a):
                self.a = a
            def __add__(self, other):
                return self.a + other.a
            __radd__ = __add__
        class B:
            def __init__(self, a):
                self.a = a
        # New-style
        class C(object):
            def __init__(self, a):
                self.a = a
            def __add__(self, other):
                return self.a + other.a
            __radd__ = __add__
        class D(object):
            def __init__(self, a):
                self.a = a

        assert A(1) + B(2) == 3
        assert B(1) + A(2) == 3
        assert A(1) + C(2) == 3
        assert C(1) + A(2) == 3
        assert A(1) + D(2) == 3
        assert D(1) + A(2) == 3
        assert C(1) + D(2) == 3
        assert D(1) + C(2) == 3

    def test_mod_failure(self):
        try:
            [] % 3
        except TypeError, e:
            assert '%' in str(e)
        else:
            assert False, "did not raise"

    def test_invalid_iterator(self):
        class x(object):
            def __iter__(self):
                return self
        raises(TypeError, iter, x())

    def test_attribute_error(self):
        class classmethodonly(classmethod):
            def __get__(self, instance, type):
                if instance is not None:
                    raise AttributeError("Must be called on a class, not an instance.")
                return super(classmethodonly, self).__get__(instance, type)

        class A(object):
            @classmethodonly
            def a(cls):
                return 3

        raises(AttributeError, lambda: A().a)

    def test_non_callable(self):
        meth = classmethod(1).__get__(1)
        raises(TypeError, meth)

    def test_isinstance_and_issubclass(self):
        class Meta(type):
            def __instancecheck__(cls, instance):
                if cls is A:
                    return True
                return False
            def __subclasscheck__(cls, sub):
                if cls is B:
                    return True
                return False
        class A:
            __metaclass__ = Meta
        class B(A):
            pass
        a = A()
        b = B()
        assert isinstance(a, A)
        assert not isinstance(a, B)
        assert isinstance(b, A)
        assert not isinstance(b, B)
        assert isinstance(4, A)
        assert not issubclass(A, A)
        assert not issubclass(B, A)
        assert issubclass(A, B)
        assert issubclass(B, B)
        assert issubclass(23, B)

    def test_truth_of_long(self):
        class X(object):
            def __len__(self): return 1L
            __nonzero__ = __len__
        assert X()
        del X.__nonzero__
        assert X()

    def test_len_overflow(self):
        import sys
        class X(object):
            def __len__(self):
                return sys.maxsize + 1
        raises(OverflowError, len, X())

    def test_len_underflow(self):
        import sys
        class X(object):
            def __len__(self):
                return -1
        raises(ValueError, len, X())
        class Y(object):
            def __len__(self):
                return -1L
        raises(ValueError, len, Y())

class AppTestWithBuiltinShortcut(AppTest_Descroperation):
    OPTIONS = {'objspace.std.builtinshortcut': True}
