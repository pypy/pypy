from __future__ import with_statement
import py
from pypy.conftest import gettestobjspace, option
from pypy.interpreter import gateway


class AppTestOldstyle(object):

    def test_simple(self):
        class A:
            a = 1
        assert A.__name__ == 'A'
        assert A.__bases__ == ()
        assert A.a == 1
        assert A.__dict__['a'] == 1
        a = A()
        a.b = 2
        assert a.b == 2
        assert a.a == 1
        assert a.__class__ is A
        assert a.__dict__ == {'b': 2}

    def test_isinstance(self):
        class A:
            pass
        class B(A):
            pass
        class C(A):
            pass
        assert isinstance(B(), A)
        assert isinstance(B(), B)
        assert not isinstance(B(), C)
        assert not isinstance(A(), B)
        assert isinstance(B(), (A, C))
        assert isinstance(B(), (C, (), (C, B)))
        assert not isinstance(B(), ())

    def test_issubclass(self):
        class A:
            pass
        class B(A):
            pass
        class C(A):
            pass
        assert issubclass(A, A)
        assert not issubclass(A, B)
        assert not issubclass(A, C)
        assert issubclass(B, A)
        assert issubclass(B, B)
        assert not issubclass(B, C)

    def test_mutate_class_special(self):
        class A:
            a = 1
        A.__name__ = 'B'
        assert A.__name__ == 'B'
        assert A.a == 1
        A.__dict__ = {'a': 5}
        assert A.a == 5
        class B:
            a = 17
            b = 18
        class C(A):
            c = 19
        assert C.a == 5
        assert C.c == 19
        C.__bases__ = (B, )
        assert C.a == 17
        assert C.b == 18
        assert C.c == 19
        C.__bases__ = (B, A)
        assert C.a == 17
        assert C.b == 18
        assert C.c == 19
        C.__bases__ = (A, B)
        assert C.a == 5
        assert C.b == 18
        assert C.c == 19

    def test_class_repr(self):
        d = {}
        exec "class A: pass" in d    # to have no __module__
        A = d['A']
        assert repr(A).startswith("<class __builtin__.A at 0x")
        A.__name__ = 'B'
        assert repr(A).startswith("<class __builtin__.B at 0x")
        A.__module__ = 'foo'
        assert repr(A).startswith("<class foo.B at 0x")
        A.__module__ = None
        assert repr(A).startswith("<class ?.B at 0x")
        del A.__module__
        assert repr(A).startswith("<class ?.B at 0x")

    def test_class_str(self):
        d = {}
        exec "class A: pass" in d    # to have no __module__
        A = d['A']
        assert str(A) == "__builtin__.A"
        A.__name__ = 'B'
        assert str(A) == "__builtin__.B"
        A.__module__ = 'foo'
        assert str(A) == "foo.B"
        A.__module__ = None
        assert str(A) == "B"
        del A.__module__
        assert str(A) == "B"

    def test_del_error_class_special(self):
        class A:
            a = 1
        raises(TypeError, "del A.__name__")
        raises(TypeError, "del A.__dict__")
        raises(TypeError, "del A.__bases__")

    def test_mutate_instance_special(self):
        class A:
            a = 1
        class B:
            a = 17
            b = 18
        a = A()
        assert isinstance(a, A)
        a.__class__ = B
        assert isinstance(a, B)
        assert a.a == 17
        assert a.b == 18


    def test_init(self):
        class A:
            a = 1
            def __init__(self, a):
                self.a = a
        a = A(2)
        assert a.a == 2
        class B:
            def __init__(self, a):
                return a

        raises(TypeError, B, 2)

    def test_method(self):
        class A:
            a = 1
            def f(self, a):
                return self.a + a
        a = A()
        assert a.f(2) == 3
        assert A.f(a, 2) == 3
        a.a = 5
        assert A.f(a, 2) == 7

    def test_inheritance(self):
        class A:
            a = 1
            b = 2
            def af(self):
                return 1
            def bf(self):
                return 2
        assert A.a == 1
        assert A.b == 2
        a = A()
        assert a.a == 1
        assert a.b == 2
        assert a.af() == 1
        assert a.bf() == 2
        assert A.af(a) == 1
        assert A.bf(a) == 2

        class B(A):
            a = 3
            c = 4
            def af(self):
                return 3
            def cf(self):
                return 4
        assert B.__bases__ == (A, )
        assert B.a == 3
        assert B.b == 2
        assert B.c == 4
        b = B()
        assert b.a == 3
        assert b.b == 2
        assert b.c == 4
        assert b.af() == 3
        assert b.bf() == 2
        assert b.cf() == 4
        assert B.af(b) == 3
        assert B.bf(b) == 2
        assert B.cf(b) == 4

    def test_inheritance_unbound_method(self):
        class A:
            def f(self):
                return 1
        raises(TypeError, A.f, 1)
        assert A.f(A()) == 1
        class B(A):
            pass
        raises(TypeError, B.f, 1)
        raises(TypeError, B.f, A())
        assert B.f(B()) == 1

    def test_len_getsetdelitem(self):
        class A:
            pass
        a = A()
        raises(AttributeError, len, a)
        raises(AttributeError, "a[5]")
        raises(AttributeError, "a[5] = 5")
        raises(AttributeError, "del a[5]")
        class A:
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __len__(self):
                return len(self.list)
            def __getitem__(self, i):
                return self.list[i]
            def __setitem__(self, i, v):
                self.list[i] = v
            def __delitem__(self, i):
                del self.list[i]

        a = A()
        assert len(a) == 5
        del a[0]
        assert len(a) == 4
        assert a[0] == 2
        a[0] = 5
        assert a[0] == 5
        assert a
        assert bool(a) == True
        del a[0]
        del a[0]
        del a[0]
        del a[0]
        assert len(a) == 0
        assert not a
        assert bool(a) == False
        a = A()
        assert a[1:3] == [2, 3]
        a[1:3] = [1, 2, 3]
        assert a.list == [1, 1, 2, 3, 4, 5]
        del a[1:4]
        assert a.list == [1, 4, 5]

    def test_len_errors(self):
        class A:
            def __len__(self):
                return long(10)
        raises(TypeError, len, A())
        class A:
            def __len__(self):
                return -1
        raises(ValueError, len, A())

    def test_call(self):
        class A:
            pass
        a = A()
        raises(AttributeError, a)
        class A:
            def __call__(self, a, b):
                return a + b
        a = A()
        assert a(1, 2) == 3

    def test_nonzero(self):
        class A:
            pass
        a = A()
        assert a
        assert bool(a) == True
        class A:
            def __init__(self, truth):
                self.truth = truth
            def __nonzero__(self):
                return self.truth
        a = A(1)
        assert a
        assert bool(a) == True
        a = A(42)
        assert a
        assert bool(a) == True
        a = A(True)
        assert a
        assert bool(a) == True
        a = A(False)
        assert not a
        assert bool(a) == False
        a = A(0)
        assert not a
        assert bool(a) == False
        a = A(-1)
        raises(ValueError, "assert a")
        a = A("hello")
        raises(TypeError, "assert a")

    def test_repr(self):
        d = {}
        exec "class A: pass" in d    # to have no __module__
        A = d['A']
        a = A()
        assert repr(a).startswith("<__builtin__.A instance at")
        assert str(a).startswith("<__builtin__.A instance at")
        A.__name__ = "Foo"
        assert repr(a).startswith("<__builtin__.Foo instance at")
        assert str(a).startswith("<__builtin__.Foo instance at")
        A.__module__ = "bar"
        assert repr(a).startswith("<bar.Foo instance at")
        assert str(a).startswith("<bar.Foo instance at")
        A.__module__ = None
        assert repr(a).startswith("<?.Foo instance at")
        assert str(a).startswith("<?.Foo instance at")
        del A.__module__
        assert repr(a).startswith("<?.Foo instance at")
        assert str(a).startswith("<?.Foo instance at")
        class A:
            def __repr__(self):
                return "foo"
        assert repr(A()) == "foo"
        assert str(A()) == "foo"

    def test_str(self):
        d = {}
        exec '''class A:
            def __str__(self):
                return "foo"
'''         in d    # to have no __module__
        A = d['A']
        a = A()
        assert repr(a).startswith("<__builtin__.A instance at")
        assert str(a) == "foo"

    def test_iter(self):
        class A:
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __iter__(self):
                return iter(self.list)
        for i, element in enumerate(A()):
            assert i + 1 == element
        class A:
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __len__(self):
                return len(self.list)
            def __getitem__(self, i):
                return self.list[i]
        for i, element in enumerate(A()):
            assert i + 1 == element

    def test_getsetdelattr(self):
        class A:
            a = 1
            def __getattr__(self, attr):
                return attr.upper()
        a = A()
        assert a.a == 1
        a.__dict__['b'] = 4
        assert a.b == 4
        assert a.c == "C"
        class A:
            a = 1
            def __setattr__(self, attr, value):
                self.__dict__[attr.lower()] = value
        a = A()
        assert a.a == 1
        a.A = 2
        assert a.a == 2
        class A:
            a = 1
            def __delattr__(self, attr):
                del self.__dict__[attr.lower()]
        a = A()
        assert a.a == 1
        a.a = 2
        assert a.a == 2
        del a.A
        assert a.a == 1

    def test_instance_override(self):
        class A:
            def __str__(self):
                return "foo"
        def __str__():
            return "bar"
        a = A()
        assert str(a) == "foo"
        a.__str__ = __str__
        assert str(a) == "bar"

    def test_unary_method(self):
        class A:
            def __pos__(self):
                 return -1
        a = A()
        assert +a == -1

    def test_cmp(self):
        class A:
            def __lt__(self, other):
                 return True
        a = A()
        b = A()
        assert a < b
        assert b < a
        assert a < 1

    def test_coerce(self):
        class B:
            def __coerce__(self, other):
                return other, self
        b = B()
        assert coerce(b, 1) == (1, b)
        class B:
            pass
        raises(TypeError, coerce, B(), [])

    def test_binaryop(self):
        class A:
            def __add__(self, other):
                return 1 + other
        a = A()
        assert a + 1 == 2
        assert a + 1.1 == 2.1

    def test_binaryop_coerces(self):
        class A:
            def __add__(self, other):
                return 1 + other
            def __coerce__(self, other):
                 return self, int(other)

        a = A()
        assert a + 1 == 2
        assert a + 1.1 == 2


    def test_binaryop_calls_coerce_always(self):
        l = []
        class A:
            def __coerce__(self, other):
                 l.append(other)

        a = A()
        raises(TypeError, "a + 1")
        raises(TypeError, "a + 1.1")
        assert l == [1, 1.1]

    def test_binaryop_raises(self):
        class A:
            def __add__(self, other):
                raise this_exception
            def __iadd__(self, other):
                raise this_exception

        a = A()
        this_exception = ValueError
        raises(ValueError, "a + 1")
        raises(ValueError, "a += 1")
        this_exception = AttributeError
        raises(AttributeError, "a + 1")
        raises(AttributeError, "a += 1")

    def test_iadd(self):
        class A:
            def __init__(self):
                self.l = []
            def __iadd__(self, other):
                 self.l.append(other)
                 return self
        a1 = a = A()
        a += 1
        assert a is a1
        a += 2
        assert a is a1
        assert a.l == [1, 2]

    def test_cmp_and_coerce(self):
        class A:
            def __coerce__(self, other):
                return (1, 2)
        assert cmp(A(), 1) == -1
        class A:
            def __cmp__(self, other):
                return 1
        class B:
            pass

        a = A()
        b = B()
        assert cmp(a, b) == 1
        assert cmp(b, a) == -1

        class A:
            def __cmp__(self, other):
                return 1L
        a = A()
        assert cmp(a, b) == 1

        class A:
            def __cmp__(self, other):
                return "hello?"
        a = A()
        raises(TypeError, cmp, a, b)

    def test_hash(self):
        import sys
        class A:
            pass
        hash(A()) # does not crash
        class A:
            def __hash__(self):
                return "hello?"
        a = A()
        raises(TypeError, hash, a)
        class A:
            def __hash__(self):
                return 1
        a = A()
        assert hash(a) == 1
        class A:
            def __cmp__(self, other):
                return 1
        a = A()
        raises(TypeError, hash, a)
        class A:
            def __eq__(self, other):
                return 1
        a = A()
        raises(TypeError, hash, a)
        bigint = sys.maxint + 1
        class A: # can return long 
            def __hash__(self):
                return long(bigint)
        a = A()
        assert hash(a) == -bigint 

    def test_index(self):
        import sys
        if sys.version_info < (2, 5):
            skip("this is not supported by CPython before version 2.4")
        class A:
            def __index__(self):
                return 1
        l = [1, 2, 3]
        assert l[A()] == 2
        class A:
            pass
        raises(TypeError, "l[A()]")

    def test_contains(self):
        class A:
            def __contains__(self, other):
                return True
        a = A()
        assert 1 in a
        assert None in a
        class A:
            pass
        a = A()
        raises(TypeError, "1 in a")
        class A:
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __iter__(self):
                return iter(self.list)
        a = A()
        for i in range(1, 6):
            assert i in a
        class A:
            def __init__(self):
                self.list = [1, 2, 3, 4, 5]
            def __len__(self):
                return len(self.list)
            def __getitem__(self, i):
                return self.list[i]
        a = A()
        for i in range(1, 6):
            assert i in a

    def test_pow(self):
        class A:
            def __pow__(self, other, mod=None):
                if mod is None:
                    return 2 ** other
                return mod ** other
        a = A()
        assert a ** 4 == 16
        assert pow(a, 4) == 16
        assert pow(a, 4, 5) == 625
        raises(TypeError, "4 ** a")
        class A:
            def __rpow__(self, other, mod=None):
                if mod is None:
                    return 2 ** other
                return mod ** other
        a = A()
        assert 4 ** a == 16
        assert pow(4, a) == 16
        raises(TypeError, "a ** 4")
        import sys
        if not hasattr(sys, 'pypy_objspaceclass'):
            skip("__rpow__(self, other, mod) seems not to work on CPython")
        assert pow(4, a, 5) == 625

    def test_getsetdelslice(self):

        class A:
            def __getslice__(self, i, j):
                return i + j
            def __setslice__(self, i, j, seq):
                self.last = (i, j, seq)
            def __delslice__(self, i, j):
                self.last = (i, j, None)
        a = A()
        assert a[1:3] == 4
        a[1:3] = [1, 2, 3]
        assert a.last == (1, 3, [1, 2, 3])
        del a[1:4]
        assert a.last == (1, 4, None)

    def test_contains_bug(self):
        class A:
            def __iter__(self):
                return self
        raises(TypeError, "1 in A()")

    def test_class_instantiation_bug(self):
        class A:
            pass
        _classobj = type(A)
        raises(TypeError, "class A(1, 2): pass")
        raises(TypeError, "_classobj(1, (), {})")
        raises(TypeError, "_classobj('abc', 1, {})")
        raises(TypeError, "_classobj('abc', (1, ), {})")
        raises(TypeError, "_classobj('abc', (), 3)")

    def test_instance_new(self):
        class A:
            b = 1
        a = A()
        a = type(a).__new__(type(a), A)
        assert a.b == 1
        a = type(a).__new__(type(a), A, None)
        assert a.b == 1
        a = type(a).__new__(type(a), A, {'c': 2})
        assert a.b == 1
        assert a.c == 2
        raises(TypeError, type(a).__new__, type(a), A, 1)

    def test_del(self):
        import gc
        l = []
        class A:
            def __del__(self):
                l.append(1)
        a = A()
        a = None
        gc.collect()
        gc.collect()
        gc.collect()
        assert l == [1]
        class B(A):
            pass
        b = B()
        b = None
        gc.collect()
        gc.collect()
        gc.collect()
        assert l == [1, 1]

    def test_catch_attributeerror_of_descriptor(self):
        def booh(self):
            raise this_exception, "booh"

        class E:
            __eq__ = property(booh)
            __iadd__ = property(booh)

        e = E()
        this_exception = AttributeError
        raises(TypeError, "e += 1")
        # does not crash
        E() == E()
        class I:
            __init__ = property(booh)
        raises(AttributeError, I)

        this_exception = ValueError
        raises(ValueError, "e += 1")

    def test_multiple_inheritance_more(self):
        l = []
        class A:    # classic class
            def save(self):
                l.append("A")
        class B(A):
            pass
        class C(A):
            def save(self):
                l.append("C")
        class D(B, C):
            pass

        D().save()
        assert l == ['A']

    def test_weakref(self):
        import weakref, gc
        class A:
            pass
        a = A()
        ref = weakref.ref(a)
        assert ref() is a
        a = None
        gc.collect()
        gc.collect()
        gc.collect()
        assert ref() is None

    def test_next(self):
        class X:
            def __iter__(self):
                return Y()
         
        class Y:
            def next(self):
                return 3
         
        for i in X():
            assert i == 3
            break

    def test_cmp_returning_notimplemented(self):
        class X:
            def __cmp__(self, other):
                return NotImplemented

        class Y:
            pass

        assert X() != 5
        assert Y() != X()

    def test_assignment_to_del(self):
        import sys
        if not hasattr(sys, 'pypy_objspaceclass'):
            skip("assignment to __del__ doesn't give a warning in CPython")

        import warnings
        
        warnings.simplefilter('error', RuntimeWarning)
        try:
            class X:
                pass
            raises(RuntimeWarning, "X.__del__ = lambda self: None")
            class Y:
                pass
            raises(RuntimeWarning, "Y().__del__ = lambda self: None")
            # but the following works
            class Z:
                def __del__(self):
                    pass
            Z().__del__ = lambda : None
        finally:
            warnings.simplefilter('default', RuntimeWarning)

    def test_context_manager(self):
        class Context:
            def __enter__(self):
                self.got_enter = True
                return 23
            def __exit__(self, exc, value, tp):
                self.got_exit = True
        c = Context()
        with c as a:
            assert c.got_enter
            assert a == 23
        assert c.got_exit

    def test_reverse(self):
        class X:
            def __reversed__(self):
                return [1, 2]
        assert reversed(X()) == [1, 2]

    def test_special_method_via_getattr(self):
        class A:
            def __getattr__(self, attr):
                print 'A getattr:', attr
                def callable(*args):
                    print 'A called:', attr + repr(args)
                    return attr + repr(args)
                return callable
        class B:
            def __getattr__(self, attr):
                print 'B getattr:', attr
                def callable(*args):
                    print 'B called:', attr, args
                    self.called = attr, args
                    if attr == '__coerce__':
                        return self, args[0]
                    return 42
                return callable
        a = A()
        a.instancevalue = 42      # does not go via __getattr__('__setattr__')
        a.__getattr__ = "hi there, ignore me, I'm in a"
        a.__setattr__ = "hi there, ignore me, I'm in a too"
        assert a.instancevalue == 42
        A.classvalue = 123
        assert a.classvalue == 123
        assert a.foobar(5) == 'foobar(5,)'
        assert a.__dict__ == {'instancevalue': 42,
                              '__getattr__': a.__getattr__,
                              '__setattr__': a.__setattr__}
        assert a.__class__ is A
        # This follows the Python 2.5 rules, more precisely.
        # It is still valid in Python 2.7 too.
        assert repr(a) == '__repr__()'
        assert str(a) == '__str__()'
        assert unicode(a) == u'__unicode__()'
        b = B()
        b.__getattr__ = "hi there, ignore me, I'm in b"
        b.__setattr__ = "hi there, ignore me, I'm in b too"
        assert 'called' not in b.__dict__      # and not e.g. ('__init__', ())
        assert len(b) == 42
        assert b.called == ('__len__', ())
        assert a[5] == '__getitem__(5,)'
        b[6] = 7
        assert b.called == ('__setitem__', (6, 7))
        del b[8]
        assert b.called == ('__delitem__', (8,))
        #
        class C:
            def __getattr__(self, name):
                if name == '__iter__':
                    return lambda: iter([3, 33, 333])
                raise AttributeError
        assert list(iter(C())) == [3, 33, 333]
        #
        class C:
            def __getattr__(self, name):
                if name == '__getitem__':
                    return lambda n: [3, 33, 333][n]
                raise AttributeError
        assert list(iter(C())) == [3, 33, 333]
        #
        assert a[:6] == '__getslice__(0, 6)'
        b[3:5] = 7
        assert b.called == ('__setslice__', (3, 5, 7))
        del b[:-1000]
        assert b.called == ('__delslice__', (0, -958))   # adds len(b)...
        assert a(5) == '__call__(5,)'
        raises(TypeError, bool, a)     # "should return an int"
        assert not not b
        #
        class C:
            def __getattr__(self, name):
                if name == '__nonzero__':
                    return lambda: False
                raise AttributeError
        assert not C()
        #
        class C:
            def __getattr__(self, name):
                if name == '__len__':
                    return lambda: 0
                raise AttributeError
        assert not C()
        #
        #assert cmp(b, 43) == 0    # because __eq__(43) returns 42, so True...
        # ... I will leave this case as XXX implement me
        assert hash(b) == 42
        assert range(100, 200)[b] == 142
        assert "foo" in b
        #
        class C:
            def __iter__(self):
                return self
            def __getattr__(self, name):
                if name == 'next':
                    return lambda: 'the next item'
                raise AttributeError
        for x in C():
            assert x == 'the next item'
            break
        #
        # XXX a really corner case: '__del__'
        #
        import operator
        op_by_name = {"neg": operator.neg,
                      "pos": operator.pos,
                      "abs": abs,
                      "invert": operator.invert,
                      "int": int,
                      "long": long}
        for opname, opfunc in op_by_name.items():
            assert opfunc(b) == 42
            called = b.called
            assert called == ("__" + opname + "__", ())
        assert oct(a) == '__oct__()'
        assert hex(a) == '__hex__()'
        #
        class JustTrunc:
            def __trunc__(self):
                return 42
        assert int(JustTrunc()) == 42
        assert long(JustTrunc()) == 42
        #
        #
        class C:
            def __getattr__(self, name):
                return lambda: 5.5
        raises(TypeError, float, b)
        assert float(C()) == 5.5
        #
        op_by_name = {'eq': operator.eq,
                      'ne': operator.ne,
                      'gt': operator.gt,
                      'lt': operator.lt,
                      'ge': operator.ge,
                      'le': operator.le,
                      'imod': operator.imod,
                      'iand': operator.iand,
                      'ipow': operator.ipow,
                      'itruediv': operator.itruediv,
                      'ilshift': operator.ilshift,
                      'ixor': operator.ixor,
                      'irshift': operator.irshift,
                      'ifloordiv': operator.ifloordiv,
                      'idiv': operator.idiv,
                      'isub': operator.isub,
                      'imul': operator.imul,
                      'iadd': operator.iadd,
                      'ior': operator.ior,
                      'or': operator.or_,
                      'and': operator.and_,
                      'xor': operator.xor,
                      'lshift': operator.lshift,
                      'rshift': operator.rshift,
                      'add': operator.add,
                      'sub': operator.sub,
                      'mul': operator.mul,
                      'div': operator.div,
                      'mod': operator.mod,
                      'divmod': divmod,
                      'floordiv': operator.floordiv,
                      'truediv': operator.truediv}
        for opname, opfunc in op_by_name.items():
            assert opfunc(b, 5) == 42
            assert b.called == ("__" + opname + "__", (5,))
        x, y = coerce(b, 5)
        assert x is b
        assert y == 5

    def test_cant_subclass_instance(self):
        class A:
            pass
        try:
            class B(type(A())):
                pass
        except TypeError:
            pass
        else:
            assert 0, "should have raised"

    def test_dict_descriptor(self):
        import sys
        if not hasattr(sys, 'pypy_objspaceclass'):
            skip("on CPython old-style instances don't have a __dict__ descriptor")
        class A:
            pass
        a = A()
        a.x = 1
        descr = type(a).__dict__['__dict__']
        assert descr.__get__(a) == {'x': 1}
        descr.__set__(a, {'x': 2})
        assert a.x == 2
        raises(TypeError, descr.__delete__, a)

    def test_partial_ordering(self):
        class A:
            def __lt__(self, other):
                return self
        a1 = A()
        a2 = A()
        assert (a1 < a2) is a1
        assert (a1 > a2) is a2

    def test_eq_order(self):
        # this gives the ordering of equality-related functions on top of
        # CPython **for old-style classes**.
        class A:
            def __eq__(self, other): return self.__class__.__name__+':A.eq'
            def __ne__(self, other): return self.__class__.__name__+':A.ne'
            def __lt__(self, other): return self.__class__.__name__+':A.lt'
            def __le__(self, other): return self.__class__.__name__+':A.le'
            def __gt__(self, other): return self.__class__.__name__+':A.gt'
            def __ge__(self, other): return self.__class__.__name__+':A.ge'
        class B:
            def __eq__(self, other): return self.__class__.__name__+':B.eq'
            def __ne__(self, other): return self.__class__.__name__+':B.ne'
            def __lt__(self, other): return self.__class__.__name__+':B.lt'
            def __le__(self, other): return self.__class__.__name__+':B.le'
            def __gt__(self, other): return self.__class__.__name__+':B.gt'
            def __ge__(self, other): return self.__class__.__name__+':B.ge'
        #
        assert (A() == B()) == 'A:A.eq'
        assert (A() != B()) == 'A:A.ne'
        assert (A() <  B()) == 'A:A.lt'
        assert (A() <= B()) == 'A:A.le'
        assert (A() >  B()) == 'A:A.gt'
        assert (A() >= B()) == 'A:A.ge'
        #
        assert (B() == A()) == 'B:B.eq'
        assert (B() != A()) == 'B:B.ne'
        assert (B() <  A()) == 'B:B.lt'
        assert (B() <= A()) == 'B:B.le'
        assert (B() >  A()) == 'B:B.gt'
        assert (B() >= A()) == 'B:B.ge'
        #
        class C(A):
            def __eq__(self, other): return self.__class__.__name__+':C.eq'
            def __ne__(self, other): return self.__class__.__name__+':C.ne'
            def __lt__(self, other): return self.__class__.__name__+':C.lt'
            def __le__(self, other): return self.__class__.__name__+':C.le'
            def __gt__(self, other): return self.__class__.__name__+':C.gt'
            def __ge__(self, other): return self.__class__.__name__+':C.ge'
        #
        assert (A() == C()) == 'A:A.eq'
        assert (A() != C()) == 'A:A.ne'
        assert (A() <  C()) == 'A:A.lt'
        assert (A() <= C()) == 'A:A.le'
        assert (A() >  C()) == 'A:A.gt'
        assert (A() >= C()) == 'A:A.ge'
        #
        assert (C() == A()) == 'C:C.eq'
        assert (C() != A()) == 'C:C.ne'
        assert (C() <  A()) == 'C:C.lt'
        assert (C() <= A()) == 'C:C.le'
        assert (C() >  A()) == 'C:C.gt'
        assert (C() >= A()) == 'C:C.ge'
        #
        class D(A):
            pass
        #
        assert (A() == D()) == 'A:A.eq'
        assert (A() != D()) == 'A:A.ne'
        assert (A() <  D()) == 'A:A.lt'
        assert (A() <= D()) == 'A:A.le'
        assert (A() >  D()) == 'A:A.gt'
        assert (A() >= D()) == 'A:A.ge'
        #
        assert (D() == A()) == 'D:A.eq'
        assert (D() != A()) == 'D:A.ne'
        assert (D() <  A()) == 'D:A.lt'
        assert (D() <= A()) == 'D:A.le'
        assert (D() >  A()) == 'D:A.gt'
        assert (D() >= A()) == 'D:A.ge'


class AppTestOldStyleClassStrDict(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("can only be run on py.py")
        def is_strdict(space, w_class):
            from pypy.objspace.std.dictmultiobject import StringDictStrategy
            w_d = w_class.getdict(space)
            return space.wrap(isinstance(w_d.strategy, StringDictStrategy))

        cls.w_is_strdict = cls.space.wrap(gateway.interp2app(is_strdict))

    def test_strdict(self):
        class A:
            a = 1
            b = 2
        assert self.is_strdict(A)

class AppTestOldStyleMapDict(AppTestOldstyle):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withmapdict": True})
        if option.runappdirect:
            py.test.skip("can only be run on py.py")
        def has_mapdict(space, w_inst):
            return space.wrap(w_inst._get_mapdict_map() is not None)
        cls.w_has_mapdict = cls.space.wrap(gateway.interp2app(has_mapdict))


    def test_has_mapdict(self):
        class A:
            def __init__(self):
                self.x = 42
        a = A()
        assert a.x == 42
        assert self.has_mapdict(a)

