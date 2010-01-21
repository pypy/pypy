import py
from pypy.interpreter import gateway
from pypy.objspace.test import test_descriptor


class AppTestUserObject:
    OPTIONS = {}    # for test_builtinshortcut.py

    def setup_class(cls):
        from pypy import conftest
        cls.space = conftest.gettestobjspace(**cls.OPTIONS)
        #
        import random
        def fn_rand():
            return cls.space.wrap(random.randrange(0, 5))
        fn_rand.unwrap_spec = []
        if conftest.option.runappdirect:
            cls.w_rand = fn_rand
        else:
            cls.w_rand = cls.space.wrap(gateway.interp2app(fn_rand))
        cls.w_runappdirect = cls.space.wrap(bool(conftest.option.runappdirect))

    def test_emptyclass(self):
        class empty(object): pass
        inst = empty()
        assert isinstance(inst, empty)
        inst.attr = 23
        assert inst.attr == 23

    def test_method(self):
        class A(object):
            def f(self, v):
                return v*42
        a = A()
        assert a.f('?') == '??????????????????????????????????????????'

    def test_unboundmethod(self):
        class A(object):
            def f(self, v):
                return v*17
        a = A()
        assert A.f(a, '!') == '!!!!!!!!!!!!!!!!!'

    def test_subclassing(self):
        for base in tuple, list, dict, str, int, float:
            class subclass(base): pass
            stuff = subclass()
            assert isinstance(stuff, base)
            assert subclass.__base__ is base

    def test_subclasstuple(self):
        class subclass(tuple): pass
        stuff = subclass()
        assert isinstance(stuff, tuple)
        stuff.attr = 23
        assert stuff.attr ==23
        assert len(stuff) ==0
        result = stuff + (1,2,3)
        assert len(result) ==3

    def test_subsubclass(self):
        class base(object):
            baseattr = 12
        class derived(base):
            derivedattr = 34
        inst = derived()
        assert isinstance(inst, base)
        assert inst.baseattr ==12
        assert inst.derivedattr ==34

    def test_descr_get(self):
        class C(object):
            class desc(object):
                def __get__(self, ob, cls=None):
                    return 42
            prop = desc()
        assert C().prop == 42

    def test_descr_set(self):
        class C(object):
            class desc(object):
                def __set__(self, ob, val):
                    ob.wibble = val
            prop = desc()
        c = C()
        c.prop = 32
        assert c.wibble == 32

    def test_descr_delete(self):
        class C(object):
            class desc(object):
                def __set__(self, ob, val):
                    oogabooga
                def __delete__(self, ob):
                    ob.wibble = 22
            prop = desc()
        c = C()
        del c.prop
        assert c.wibble == 22

    def test_class_setattr(self):
        class C(object):
            pass
        C.a = 1
        assert hasattr(C, 'a')
        assert C.a == 1

    def test_add(self):
        class C(object):
            def __add__(self, other):
                return self, other
        c1 = C()
        assert c1+3 == (c1, 3)

    def test_call(self):
        class C(object):
            def __call__(self, *args):
                return args
        c1 = C()
        assert c1() == ()
        assert c1(5) == (5,)
        assert c1("hello", "world") == ("hello", "world")

    def test_getattribute(self):
        class C(object):
            def __getattribute__(self, name):
                return '->' + name
        c1 = C()
        assert c1.a == '->a'
        c1.a = 5
        assert c1.a == '->a'

    def test_getattr(self):
        class C(object):
            def __getattr__(self, name):
                return '->' + name
        c1 = C()
        assert c1.a == '->a'
        c1.a = 5
        assert c1.a == 5

    def test_dict(self):
        class A(object):
            pass
        class B(A):
            pass
        assert not '__dict__' in object.__dict__
        assert '__dict__' in A.__dict__
        assert not '__dict__' in B.__dict__
        a = A()
        a.x = 5
        assert a.__dict__ == {'x': 5}
        a.__dict__ = {'y': 6}
        assert a.y == 6
        assert not hasattr(a, 'x')

    def test_del(self):
        import gc
        lst = []
        class A(object):
            def __del__(self):
                lst.append(42)
        A()
        gc.collect()
        assert lst == [42]

    def test_del_exception(self):
        import sys, StringIO, gc
        class A(object):
            def __del__(self):
                yaddadlaouti
        prev = sys.stderr
        try:
            sys.stderr = StringIO.StringIO()
            A()
            gc.collect()
            res = sys.stderr.getvalue()
            A()
            gc.collect()
            res2 = sys.stderr.getvalue()
        finally:
            sys.stderr = prev
        assert res.startswith('Exception')
        assert 'NameError' in res
        assert 'yaddadlaouti' in res
        assert 'ignored' in res
        assert res.count('\n') == 1    # a single line
        assert res2.count('\n') == 2   # two lines
        line2 = res2.split('\n')[1]
        assert line2.startswith('Exception')
        assert 'NameError' in line2
        assert 'yaddadlaouti' in line2
        assert 'ignored' in line2

    def test_instance_overrides_meth(self):
        class C(object):
            def m(self):
                return "class"
        assert C().m() == 'class'
        c = C()
        c.m = lambda: "instance"
        res = c.m()
        assert res == "instance"

    def test_override_builtin_methods(self):
        class myint(int):
            def __add__(self, other):
                return 'add'
            def __rsub__(self, other):
                return 'rsub'
        assert myint(3) + 5 == 'add'
        assert 5 + myint(3) == 8
        assert myint(3) - 5 == -2
        assert 5 - myint(3) == 'rsub'

    def test_repr(self):
        class Foo(object):
            pass
        Foo.__module__ = 'a.b.c'
        s = repr(Foo())
        assert s.startswith('<a.b.c.Foo object at ')

    def test_del_attr(self):
        class Foo(object):
            def __init__(self):
                self.x = 3

        foo = Foo()
        del foo.x

        raises(AttributeError, "del foo.x")

        class Foo:
            def __init__(self):
                self.x = 3

        foo = Foo()
        del foo.x
        raises(AttributeError, "del foo.x")

    def test_del_attr_class(self):
        class Foo:
            pass

        raises(AttributeError, "del Foo.x")

    def test_hash(self):
        if not hasattr(self, 'runappdirect'):
            skip("disabled")
        if self.runappdirect:
            total = 500000
        else:
            total = 50
        #
        class A(object):
            hash = None
        tail = any = A()
        tail.next = tail
        i = 0
        while i < total:
            a = A()
            a.next = tail.next
            tail.next = a
            for j in range(self.rand()):
                any = any.next
            if any.hash is None:
                any.hash = hash(any)
            else:
                assert any.hash == hash(any)
            i += 1
        i = 0
        while i < total:
            if any.hash is not None:
                assert any.hash == hash(any)
            any = any.next
            i += 1


class AppTestWithMultiMethodVersion2(AppTestUserObject):
    OPTIONS = {}    # for test_builtinshortcut.py

    def setup_class(cls):
        from pypy import conftest
        from pypy.objspace.std import multimethod

        cls.prev_installer = multimethod.Installer
        multimethod.Installer = multimethod.InstallerVersion2
        if conftest.option.runappdirect:
            py.test.skip("Cannot run different installers when runappdirect")
        config = conftest.make_config(conftest.option, **cls.OPTIONS)
        cls.space = conftest.maketestobjspace(config)

    def teardown_class(cls):
        from pypy.objspace.std import multimethod
        multimethod.Installer = cls.prev_installer


class AppTestWithGetAttributeShortcut(AppTestUserObject):
    OPTIONS = {"objspace.std.getattributeshortcut": True}


class AppTestDescriptorWithGetAttributeShortcut(
    test_descriptor.AppTest_Descriptor):
    # for the individual tests see
    # ====> ../../test/test_descriptor.py

    OPTIONS = {"objspace.std.getattributeshortcut": True}
