import autopath

objspacename = 'std'

class AppTestUserObject:
    def test_emptyclass(self):
        class empty: pass
        inst = empty()
        assert isinstance(inst, empty)
        inst.attr=23
        assert inst.attr ==23

    def test_method(self):
        class A:
            def f(self, v):
                return v*42
        a = A()
        assert a.f('?') == '??????????????????????????????????????????'

    def test_unboundmethod(self):
        class A:
            def f(self, v):
                return v*17
        a = A()
        assert A.f(a, '!') == '!!!!!!!!!!!!!!!!!'

    def test_subclassing(self):
        for base in tuple, list, dict, str, int, float:
            try:
                class subclass(base): pass
                stuff = subclass()
            except:
                print 'not subclassable:', base
                if base is not dict:  # XXX must be fixed
                    raise
            else:
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
        class base:
            baseattr = 12
        class derived(base):
            derivedattr = 34
        inst = derived()
        assert isinstance(inst, base)
        assert inst.baseattr ==12
        assert inst.derivedattr ==34

    def test_descr_get(self):
        class C:
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
        class C:
            pass
        C.a = 1
        assert hasattr(C, 'a')
        assert C.a == 1

    def test_add(self):
        class C:
            def __add__(self, other):
                return self, other
        c1 = C()
        assert c1+3 == (c1, 3)

    def test_call(self):
        class C:
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
        class C:
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
