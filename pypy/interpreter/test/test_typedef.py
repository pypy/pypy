from pypy.interpreter import typedef
from pypy.tool.udir import udir
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.gateway import ObjSpace

# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class AppTestTraceBackAttributes:

    def test_newstring(self):
        # XXX why is this called newstring?
        import sys
        def f():
            raise TypeError, "hello"

        def g():
            f()

        try:
            g()
        except:
            typ,val,tb = sys.exc_info()
        else:
            raise AssertionError, "should have raised"
        assert hasattr(tb, 'tb_frame')
        assert hasattr(tb, 'tb_lasti')
        assert hasattr(tb, 'tb_lineno')
        assert hasattr(tb, 'tb_next')

    def test_descr_dict(self):
        def f():
            pass
        dictdescr = type(f).__dict__['__dict__']   # only for functions
        assert dictdescr.__get__(f) is f.__dict__
        raises(TypeError, dictdescr.__get__, 5)
        d = {}
        dictdescr.__set__(f, d)
        assert f.__dict__ is d
        raises(TypeError, dictdescr.__set__, f, "not a dict")
        raises(TypeError, dictdescr.__set__, 5, d)
        # in PyPy, the following descr applies to any object that has a dict,
        # but not to objects without a dict, obviously
        dictdescr = type.__dict__['__dict__']
        raises(TypeError, dictdescr.__get__, 5)
        raises(TypeError, dictdescr.__set__, 5, d)

    def test_descr_member_descriptor(self):
        class X(object):
            __slots__ = ['x']
        member = X.x
        assert member.__name__ == 'x'
        assert member.__objclass__ is X
        raises((TypeError, AttributeError), "member.__name__ = 'x'")
        raises((TypeError, AttributeError), "member.__objclass__ = X")

    def test_descr_getsetproperty(self):
        from types import FrameType
        assert FrameType.f_lineno.__name__ == 'f_lineno'
        assert FrameType.f_lineno.__objclass__ is FrameType
        class A(object):
            pass
        assert A.__dict__['__dict__'].__name__ == '__dict__'


class TestTypeDef:

    def test_subclass_cache(self):
        # check that we don't create more than 6 subclasses of a
        # given W_XxxObject (instead of the 16 that follow from
        # all combinations)
        space = self.space
        sources = []
        for hasdict in [False, True]:
            for wants_slots in [False, True]:
                for needsdel in [False, True]:
                    for weakrefable in [False, True]:
                        print 'Testing case', hasdict, wants_slots,
                        print needsdel, weakrefable
                        slots = []
                        checks = []

                        if hasdict:
                            slots.append('__dict__')
                            checks.append('x.foo=5; x.__dict__')
                        else:
                            checks.append('raises(AttributeError, "x.foo=5");'
                                        'raises(AttributeError, "x.__dict__")')

                        if wants_slots:
                            slots.append('a')
                            checks.append('x.a=5; assert X.a.__get__(x)==5')
                        else:
                            checks.append('')

                        if weakrefable:
                            slots.append('__weakref__')
                            checks.append('import _weakref;_weakref.ref(x)')
                        else:
                            checks.append('')

                        if needsdel:
                            methodname = '__del__'
                            checks.append('X();X();X();'
                                          'import gc;gc.collect();'
                                          'assert seen')
                        else:
                            methodname = 'spam'
                            checks.append('assert "Del" not in irepr')

                        assert len(checks) == 4
                        space.appexec([], """():
                            seen = []
                            class X(list):
                                __slots__ = %r
                                def %s(self):
                                    seen.append(1)
                            x = X()
                            import __pypy__
                            irepr = __pypy__.internal_repr(x)
                            print irepr
                            %s
                            %s
                            %s
                            %s
                        """ % (slots, methodname, checks[0], checks[1],
                               checks[2], checks[3]))
        subclasses = {}
        for key, subcls in typedef._subclass_cache.items():
            if key[0] is not space.config:
                continue
            cls = key[1]
            subclasses.setdefault(cls, {})
            prevsubcls = subclasses[cls].setdefault(subcls.__name__, subcls)
            assert subcls is prevsubcls
        for cls, set in subclasses.items():
            assert len(set) <= 6, "%s has %d subclasses:\n%r" % (
                cls, len(set), list(set))

    def test_getsetproperty(self):
        class W_SomeType(Wrappable):
            pass
        def fget(self, space, w_self):
            assert self is prop
        prop = typedef.GetSetProperty(fget, use_closure=True)
        W_SomeType.typedef = typedef.TypeDef(
            'some_type',
            x=prop)
        w_obj = self.space.wrap(W_SomeType())
        assert self.space.getattr(w_obj, self.space.wrap('x')) is self.space.w_None

    def test_getsetproperty_arguments(self):
        class W_SomeType(Wrappable):
            def fget1(space, w_self):
                assert isinstance(space, ObjSpace)
                assert isinstance(w_self, W_SomeType)
            def fget2(self, space):
                assert isinstance(space, ObjSpace)
                assert isinstance(self, W_SomeType)
        W_SomeType.typedef = typedef.TypeDef(
            'some_type',
            x1=typedef.GetSetProperty(W_SomeType.fget1),
            x2=typedef.GetSetProperty(W_SomeType.fget2),
            )
        space = self.space
        w_obj = space.wrap(W_SomeType())
        assert space.getattr(w_obj, space.wrap('x1')) == space.w_None
        assert space.getattr(w_obj, space.wrap('x2')) == space.w_None

    def test_unhashable(self):
        class W_SomeType(Wrappable):
            pass
        W_SomeType.typedef = typedef.TypeDef(
            'some_type',
            __hash__ = None)
        w_obj = self.space.wrap(W_SomeType())
        self.space.appexec([w_obj], """(obj):
            assert type(obj).__hash__ is None
            err = raises(TypeError, hash, obj)
            assert err.value.message == "'some_type' objects are unhashable"
            """)


class AppTestTypeDef:

    def setup_class(cls):
        path = udir.join('AppTestTypeDef.txt')
        path.write('hello world\n')
        cls.w_path = cls.space.wrap(str(path))

    def test_destructor(self):
        import gc, os
        seen = []
        class MyFile(file):
            def __del__(self):
                seen.append(10)
                seen.append(os.lseek(self.fileno(), 2, 0))
        f = MyFile(self.path, 'r')
        fd = f.fileno()
        seen.append(os.lseek(fd, 5, 0))
        del f
        gc.collect(); gc.collect(); gc.collect()
        lst = seen[:]
        assert lst == [5, 10, 2]
        raises(OSError, os.lseek, fd, 7, 0)

    def test_method_attrs(self):
        import sys
        class A(object):
            def m(self):
                "aaa"
            m.x = 3

        bm = A().m
        assert bm.__func__ is bm.im_func
        assert bm.__self__ is bm.im_self
        assert bm.__doc__ == "aaa"
        assert bm.x == 3
        raises(AttributeError, setattr, bm, 'x', 15)
