"""
NOTE: these tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest, DefaultExtensionTemplate


class PointTemplate(DefaultExtensionTemplate):
    """
    ExtensionTemplate with extra markers which helps to define again and again
    a simple Point type. Note that every test can use a different combination
    of markers, to test different features.
    """

    def DEFINE_PointObject(self):
        return """
            typedef struct {
                HPyObject_HEAD
                long x;
                long y;
            } PointObject;
        """

    def DEFINE_Point_new(self):
        return """
            HPyDef_SLOT(Point_new, Point_new_impl, HPy_tp_new)
            static HPy Point_new_impl(HPyContext ctx, HPy cls, HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                long x, y;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "ll", &x, &y))
                    return HPy_NULL;
                PointObject *point;
                HPy h_point = HPy_New(ctx, cls, &point);
                if (HPy_IsNull(h_point))
                    return HPy_NULL;
                point->x = x;
                point->y = y;
                return h_point;
            }
        """

    def DEFINE_Point_xy(self):
        return """
            HPyDef_MEMBER(Point_x, "x", HPyMember_LONG, offsetof(PointObject, x))
            HPyDef_MEMBER(Point_y, "y", HPyMember_LONG, offsetof(PointObject, y))
        """

    def EXPORT_POINT_TYPE(self, *defines):
        defines += ('NULL',)
        defines = ', '.join(defines)
        #
        self.EXPORT_TYPE('"Point"', "Point_spec")
        return """
            static HPyDef *Point_defines[] = { %s };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .defines = Point_defines
            };
        """ % defines



class TestType(HPyTest):

    ExtensionTemplate = PointTemplate

    def test_simple_type(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        assert isinstance(mod.Dummy, type)
        assert mod.Dummy.__name__ == 'Dummy'
        assert mod.Dummy.__module__ == 'mytest'
        assert isinstance(mod.Dummy(), mod.Dummy)

        class Sub(mod.Dummy):
            pass
        assert isinstance(Sub(), mod.Dummy)

    def test_doc_string(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .doc = "A succinct description.",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        assert mod.Dummy.__doc__ == "A succinct description."

    def test_HPyDef_SLOT(self):
        mod = self.make_module("""
            HPyDef_SLOT(Dummy_repr, Dummy_repr_impl, HPy_tp_repr);
            static HPy Dummy_repr_impl(HPyContext ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "<Dummy>");
            }

            HPyDef_SLOT(Dummy_abs, Dummy_abs_impl, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            static HPyDef *Dummy_defines[] = {
                &Dummy_repr,
                &Dummy_abs,
                NULL
            };
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .defines = Dummy_defines
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert repr(d) == '<Dummy>'
        assert abs(d) == 1234

    def test_HPyDef_METH(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(Dummy_foo, "foo", Dummy_foo_impl, HPyFunc_O, .doc="hello")
            static HPy Dummy_foo_impl(HPyContext ctx, HPy self, HPy arg)
            {
                return HPy_Add(ctx, arg, arg);
            }

            HPyDef_METH(Dummy_bar, "bar", Dummy_bar_impl, HPyFunc_NOARGS)
            static HPy Dummy_bar_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            HPyDef_METH(Dummy_identity, "identity", Dummy_identity_impl, HPyFunc_NOARGS)
            static HPy Dummy_identity_impl(HPyContext ctx, HPy self)
            {
                return HPy_Dup(ctx, self);
            }

            static HPyDef *dummy_type_defines[] = {
                    &Dummy_foo,
                    &Dummy_bar,
                    &Dummy_identity,
                    NULL
            };

            static HPyType_Spec dummy_type_spec = {
                .name = "mytest.Dummy",
                .defines = dummy_type_defines
            };

            @EXPORT_TYPE("Dummy", dummy_type_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert d.foo.__doc__ == 'hello'
        assert d.bar.__doc__ is None
        assert d.foo(21) == 42
        assert d.bar() == 1234
        assert d.identity() is d
        with pytest.raises(TypeError):
            mod.Dummy.identity()
        class A: pass
        with pytest.raises(TypeError):
            mod.Dummy.identity(A())

    def test_HPy_New(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_METH(Point_foo, "foo", Point_foo_impl, HPyFunc_NOARGS)
            static HPy Point_foo_impl(HPyContext ctx, HPy self)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_foo)
            @INIT
        """)
        p1 = mod.Point(7, 3)
        assert p1.foo() == 73
        p2 = mod.Point(4, 2)
        assert p2.foo() == 42

    def test_refcount(self):
        import pytest
        import sys
        if not self.supports_refcounts():
            pytest.skip()
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new
            @EXPORT_POINT_TYPE(&Point_new)
            @INIT
        """)
        tp = mod.Point
        init_refcount = sys.getrefcount(tp)
        p = tp(1, 2)
        assert sys.getrefcount(tp) == init_refcount + 1
        p = None
        assert sys.getrefcount(tp) == init_refcount

    def test_HPyDef_Member_basic(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new
            @DEFINE_Point_xy
            @EXPORT_POINT_TYPE(&Point_new, &Point_x, &Point_y)
            @INIT
        """)
        p = mod.Point(7, 3)
        assert p.x == 7
        assert p.y == 3
        p.x = 123
        p.y = 456
        assert p.x == 123
        assert p.y == 456

    def test_HPyDef_Member_integers(self):
        import pytest
        BIGNUM = 2**200
        for kind, c_type in [
                ('SHORT', 'short'),
                ('INT', 'int'),
                ('LONG', 'long'),
                ('USHORT', 'unsigned short'),
                ('UINT', 'unsigned int'),
                ('ULONG', 'unsigned long'),
                ('BYTE', 'char'),
                ('UBYTE', 'unsigned char'),
                ('LONGLONG', 'long long'),
                ('ULONGLONG', 'unsigned long long'),
                ('HPYSSIZET', 'HPy_ssize_t'),
                ]:
            mod = self.make_module("""
            typedef struct {
                HPyObject_HEAD
                %(c_type)s member;
            } FooObject;

            HPyDef_SLOT(Foo_new, Foo_new_impl, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext ctx, HPy cls, HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                FooObject *foo;
                HPy h_obj = HPy_New(ctx, cls, &foo);
                if (HPy_IsNull(h_obj))
                    return HPy_NULL;
                foo->member = 42;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_member, "member", HPyMember_%(kind)s, offsetof(FooObject, member))

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_member,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "test_%(kind)s.Foo",
                .basicsize = sizeof(FooObject),
                .defines = Foo_defines
            };

            @EXPORT_TYPE("Foo", Foo_spec)
            @INIT
            """ % {'c_type': c_type, 'kind': kind}, name='test_%s' % (kind,))
            foo = mod.Foo()
            assert foo.member == 42
            foo.member = 43
            assert foo.member == 43
            with pytest.raises(OverflowError):
                foo.member = BIGNUM
            with pytest.raises(TypeError):
                foo.member = None
            with pytest.raises(TypeError):
                del foo.member

    def test_HPyDef_Member_readonly_integers(self):
        import pytest
        for kind, c_type in [
                ('SHORT', 'short'),
                ('INT', 'int'),
                ('LONG', 'long'),
                ('USHORT', 'unsigned short'),
                ('UINT', 'unsigned int'),
                ('ULONG', 'unsigned long'),
                ('BYTE', 'char'),
                ('UBYTE', 'unsigned char'),
                ('LONGLONG', 'long long'),
                ('ULONGLONG', 'unsigned long long'),
                ('HPYSSIZET', 'HPy_ssize_t'),
                ]:
            mod = self.make_module("""
            typedef struct {
                HPyObject_HEAD
                %(c_type)s member;
            } FooObject;

            HPyDef_SLOT(Foo_new, Foo_new_impl, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext ctx, HPy cls, HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                FooObject *foo;
                HPy h_obj = HPy_New(ctx, cls, &foo);
                if (HPy_IsNull(h_obj))
                    return HPy_NULL;
                foo->member = 42;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_member, "member", HPyMember_%(kind)s, offsetof(FooObject, member), .readonly=1)

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_member,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "test_%(kind)s.Foo",
                .basicsize = sizeof(FooObject),
                .defines = Foo_defines
            };

            @EXPORT_TYPE("Foo", Foo_spec)
            @INIT
            """ % {'c_type': c_type, 'kind': kind}, name='test_%s' % (kind,))
            foo = mod.Foo()
            assert foo.member == 42
            with pytest.raises(AttributeError):
                foo.member = 43
            assert foo.member == 42
            with pytest.raises(AttributeError):
                del foo.member
            assert foo.member == 42

    def test_HPyDef_Member_others(self):
        import pytest
        mod = self.make_module("""
            #include <string.h>
            typedef struct {
                HPyObject_HEAD
                float FLOAT_member;
                double DOUBLE_member;
                const char* STRING_member;
                const char *STRING_null_member;
                char CHAR_member;
                char ISTRING_member[6];
                char BOOL_member;
            } FooObject;

            HPyDef_SLOT(Foo_new, Foo_new_impl, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext ctx, HPy cls, HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                FooObject *foo;
                HPy h_obj = HPy_New(ctx, cls, &foo);
                if (HPy_IsNull(h_obj))
                    return HPy_NULL;
                foo->FLOAT_member = 1.;
                foo->DOUBLE_member = 1.;
                const char * s = "Hello";
                foo->STRING_member = s;
                foo->STRING_null_member = NULL;
                foo->CHAR_member = 'A';
                strncpy(foo->ISTRING_member, "Hello", 6);
                foo->BOOL_member = 0;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_FLOAT_member, "FLOAT_member", HPyMember_FLOAT, offsetof(FooObject, FLOAT_member))
            HPyDef_MEMBER(Foo_DOUBLE_member, "DOUBLE_member", HPyMember_DOUBLE, offsetof(FooObject, DOUBLE_member))
            HPyDef_MEMBER(Foo_STRING_member, "STRING_member", HPyMember_STRING, offsetof(FooObject, STRING_member))
            HPyDef_MEMBER(Foo_STRING_null_member, "STRING_null_member", HPyMember_STRING, offsetof(FooObject, STRING_null_member))
            HPyDef_MEMBER(Foo_CHAR_member, "CHAR_member", HPyMember_CHAR, offsetof(FooObject, CHAR_member))
            HPyDef_MEMBER(Foo_ISTRING_member, "ISTRING_member", HPyMember_STRING_INPLACE, offsetof(FooObject, ISTRING_member))
            HPyDef_MEMBER(Foo_BOOL_member, "BOOL_member", HPyMember_BOOL, offsetof(FooObject, BOOL_member))
            HPyDef_MEMBER(Foo_NONE_member, "NONE_member", HPyMember_NONE, offsetof(FooObject, FLOAT_member))

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_FLOAT_member,
                    &Foo_DOUBLE_member,
                    &Foo_STRING_member,
                    &Foo_STRING_null_member,
                    &Foo_CHAR_member,
                    &Foo_ISTRING_member,
                    &Foo_BOOL_member,
                    &Foo_NONE_member,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "mytest.Foo",
                .basicsize = sizeof(FooObject),
                .defines = Foo_defines
            };

            @EXPORT_TYPE("Foo", Foo_spec)
            @INIT
            """)
        foo = mod.Foo()
        assert foo.FLOAT_member == 1.
        foo.FLOAT_member = 0.1
        assert foo.FLOAT_member != 0.1
        assert abs(foo.FLOAT_member - 0.1) < 1e-8
        with pytest.raises(TypeError):
            del foo.FLOAT_member

        assert foo.DOUBLE_member == 1.
        foo.DOUBLE_member = 0.1
        assert foo.DOUBLE_member == 0.1  # exactly
        with pytest.raises(TypeError):
            del foo.DOUBLE_member

        assert foo.STRING_member == "Hello"
        assert foo.STRING_null_member is None
        with pytest.raises(TypeError):
            foo.STRING_member = "world"
        with pytest.raises(TypeError):
            del foo.STRING_member

        assert foo.CHAR_member == 'A'
        foo.CHAR_member = 'B'
        assert foo.CHAR_member == 'B'
        with pytest.raises(TypeError):
            foo.CHAR_member = 'ABC'
        with pytest.raises(TypeError):
            del foo.CHAR_member

        assert foo.ISTRING_member == "Hello"
        with pytest.raises(TypeError):
            foo.ISTRING_member = "world"
        with pytest.raises(TypeError):
            del foo.ISTRING_member

        assert foo.BOOL_member is False
        foo.BOOL_member = True
        assert foo.BOOL_member is True
        with pytest.raises(TypeError):
            foo.BOOL_member = 1
        with pytest.raises(TypeError):
            del foo.BOOL_member

        assert foo.NONE_member is None
        with pytest.raises((SystemError, TypeError)):  # CPython quirk/bug
            foo.NONE_member = None
        with pytest.raises(TypeError):
            del foo.NONE_member

    def test_HPyDef_Member_readonly_others(self):
        import pytest
        mod = self.make_module("""
            #include <string.h>
            typedef struct {
                HPyObject_HEAD
                float FLOAT_member;
                double DOUBLE_member;
                const char* STRING_member;
                char CHAR_member;
                char ISTRING_member[6];
                char BOOL_member;
            } FooObject;

            HPyDef_SLOT(Foo_new, Foo_new_impl, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext ctx, HPy cls, HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                FooObject *foo;
                HPy h_obj = HPy_New(ctx, cls, &foo);
                if (HPy_IsNull(h_obj))
                    return HPy_NULL;
                foo->FLOAT_member = 1.;
                foo->DOUBLE_member = 1.;
                const char * s = "Hello";
                foo->STRING_member = s;
                foo->CHAR_member = 'A';
                strncpy(foo->ISTRING_member, "Hello", 6);
                foo->BOOL_member = 0;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_FLOAT_member, "FLOAT_member", HPyMember_FLOAT, offsetof(FooObject, FLOAT_member), .readonly=1)
            HPyDef_MEMBER(Foo_DOUBLE_member, "DOUBLE_member", HPyMember_DOUBLE, offsetof(FooObject, DOUBLE_member), .readonly=1)
            HPyDef_MEMBER(Foo_STRING_member, "STRING_member", HPyMember_STRING, offsetof(FooObject, STRING_member), .readonly=1)
            HPyDef_MEMBER(Foo_CHAR_member, "CHAR_member", HPyMember_CHAR, offsetof(FooObject, CHAR_member), .readonly=1)
            HPyDef_MEMBER(Foo_ISTRING_member, "ISTRING_member", HPyMember_STRING_INPLACE, offsetof(FooObject, ISTRING_member), .readonly=1)
            HPyDef_MEMBER(Foo_BOOL_member, "BOOL_member", HPyMember_BOOL, offsetof(FooObject, BOOL_member), .readonly=1)
            HPyDef_MEMBER(Foo_NONE_member, "NONE_member", HPyMember_NONE, offsetof(FooObject, FLOAT_member), .readonly=1)

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_FLOAT_member,
                    &Foo_DOUBLE_member,
                    &Foo_STRING_member,
                    &Foo_CHAR_member,
                    &Foo_ISTRING_member,
                    &Foo_BOOL_member,
                    &Foo_NONE_member,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "mytest.Foo",
                .basicsize = sizeof(FooObject),
                .defines = Foo_defines
            };

            @EXPORT_TYPE("Foo", Foo_spec)
            @INIT
            """)
        foo = mod.Foo()
        assert foo.FLOAT_member == 1.
        with pytest.raises(AttributeError):
            foo.FLOAT_member = 0.1
        assert foo.DOUBLE_member == 1.
        with pytest.raises(AttributeError):
            foo.DOUBLE_member = 0.1

        assert foo.STRING_member == "Hello"
        with pytest.raises(AttributeError):
            foo.STRING_member = "world"
        with pytest.raises(AttributeError):
            del foo.STRING_member

        assert foo.CHAR_member == 'A'
        with pytest.raises(AttributeError):
            foo.CHAR_member = 'B'
        with pytest.raises(AttributeError):
            foo.CHAR_member = 'ABC'
        with pytest.raises(AttributeError):
            del foo.CHAR_member

        assert foo.ISTRING_member == "Hello"
        with pytest.raises(AttributeError):
            foo.ISTRING_member = "world"
        with pytest.raises(AttributeError):
            del foo.ISTRING_member

        assert foo.BOOL_member is False
        with pytest.raises(AttributeError):
            foo.BOOL_member = True
        with pytest.raises(AttributeError):
            foo.BOOL_member = 1
        with pytest.raises(AttributeError):
            del foo.BOOL_member

        assert foo.NONE_member is None
        with pytest.raises(AttributeError):
            foo.NONE_member = None
        with pytest.raises(AttributeError):
            del foo.NONE_member


    def test_HPyType_GenericNew(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_xy

            HPyDef_SLOT(Point_new, HPyType_GenericNew, HPy_tp_new)

            @EXPORT_POINT_TYPE(&Point_new, &Point_x, &Point_y)
            @INIT
        """)
        p = mod.Point()
        assert p.x == 0
        assert p.y == 0

    def test_HPyDef_GET(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_GET(Point_z, "z", Point_z_get)
            static HPy Point_z_get(HPyContext ctx, HPy self, void *closure)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_z)
            @INIT
        """)
        p = mod.Point(7, 3)
        assert p.z == 73

    def test_HPyDef_GETSET(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_GETSET(Point_z, "z", Point_z_get, Point_z_set, .closure=(void *)1000)
            static HPy Point_z_get(HPyContext ctx, HPy self, void *closure)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y + (long)closure);
            }
            static int Point_z_set(HPyContext ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                long current = point->x*10 + point->y + (long)closure;
                long target = HPyLong_AsLong(ctx, value);  // assume no exception
                point->y += target - current;
                return 0;
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_z)
            @INIT
        """)
        p = mod.Point(7, 3)
        assert p.z == 1073
        p.z = 1075
        assert p.z == 1075

    def test_HPyDef_SET(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new
            @DEFINE_Point_xy

            HPyDef_SET(Point_z, "z", Point_z_set, .closure=(void *)1000)
            static int Point_z_set(HPyContext ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = HPy_CAST(ctx, PointObject, self);
                long current = point->x*10 + point->y + (long)closure;
                long target = HPyLong_AsLong(ctx, value);  // assume no exception
                point->y += target - current;
                return 0;
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_x, &Point_y, &Point_z)
            @INIT
        """)
        p = mod.Point(7, 3)
        assert p.y == 3
        p.z = 1075
        assert p.y == 5

    def test_specparam_base(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
            };

            static void make_Dummy(HPyContext ctx, HPy module)
            {
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { 0 }
                };
                HPy h_Dummy = HPyType_FromSpec(ctx, &Dummy_spec, param);
                if (HPy_IsNull(h_Dummy))
                    return;
                HPy_SetAttr_s(ctx, module, "Dummy", h_Dummy);
                HPy_Close(ctx, h_Dummy);
            }
            @EXTRA_INIT_FUNC(make_Dummy)
            @INIT
        """)
        assert isinstance(mod.Dummy, type)
        assert mod.Dummy.__name__ == 'Dummy'
        assert mod.Dummy.__module__ == 'mytest'
        assert issubclass(mod.Dummy, int)
        assert isinstance(mod.Dummy(), mod.Dummy)
        assert mod.Dummy() == 0
        assert mod.Dummy(42) == 42

        class Sub(mod.Dummy):
            pass
        assert isinstance(Sub(), mod.Dummy)

    def test_specparam_basestuple(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
            };

            static void make_Dummy(HPyContext ctx, HPy module)
            {
                HPy h_bases = HPyTuple_Pack(ctx, 1, ctx->h_LongType);
                if (HPy_IsNull(h_bases))
                    return;
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_BasesTuple, h_bases },
                    { 0 }
                };
                HPy h_Dummy = HPyType_FromSpec(ctx, &Dummy_spec, param);
                HPy_Close(ctx, h_bases);
                if (HPy_IsNull(h_Dummy))
                    return;
                HPy_SetAttr_s(ctx, module, "Dummy", h_Dummy);
                HPy_Close(ctx, h_Dummy);
            }
            @EXTRA_INIT_FUNC(make_Dummy)
            @INIT
        """)
        assert isinstance(mod.Dummy, type)
        assert mod.Dummy.__name__ == 'Dummy'
        assert mod.Dummy.__module__ == 'mytest'
        assert issubclass(mod.Dummy, int)
        assert isinstance(mod.Dummy(), mod.Dummy)
        assert mod.Dummy() == 0
        assert mod.Dummy(42) == 42

        class Sub(mod.Dummy):
            pass
        assert isinstance(Sub(), mod.Dummy)
