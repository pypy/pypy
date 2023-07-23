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

    _CURRENT_STRUCT = None

    _STRUCT_BEGIN_FORMAT = """
        typedef struct {{
    """

    _STRUCT_END_FORMAT = """
        }} {struct_name};
        {type_helpers}
    """

    _METACLASS_STRUCT_BEGIN_FORMAT = """
        typedef struct {{
    """

    _METACLASS_STRUCT_END_FORMAT = """
        }} {struct_name};
        HPyType_HELPERS({struct_name}, HPyType_BuiltinShape_Type)
    """

    def TYPE_STRUCT_BEGIN(self, struct_name):
        assert self._CURRENT_STRUCT is None
        self._CURRENT_STRUCT = struct_name
        return self._STRUCT_BEGIN_FORMAT.format(struct_name=struct_name)

    def TYPE_STRUCT_END(self, builtin_shape=None):
        assert self._CURRENT_STRUCT is not None
        struct_name = self._CURRENT_STRUCT
        self._CURRENT_STRUCT = None
        if builtin_shape:
            type_helpers = "HPyType_HELPERS({struct_name}, {builtin_shape})"\
                .format(struct_name=struct_name, builtin_shape=builtin_shape)
        else:
            type_helpers = "HPyType_HELPERS({struct_name})"\
                .format(struct_name=struct_name)
        return self._STRUCT_END_FORMAT.format(struct_name=struct_name,
                                              type_helpers=type_helpers)

    def DEFAULT_SHAPE(self):
        return "/* default object shape */"

    def DEFINE_PointObject(self, builtin_shape=None):
        type_begin = self.TYPE_STRUCT_BEGIN("PointObject")
        type_end = self.TYPE_STRUCT_END(builtin_shape=builtin_shape)
        return """
            {type_begin}
                long x;
                long y;
            {type_end}
        """.format(type_begin=type_begin, type_end=type_end)

    def DEFINE_Point_new(self):
        return """
            HPyDef_SLOT(Point_new, HPy_tp_new)
            static HPy Point_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
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

    def DEFINE_Point_call(self):
        return """
            HPyDef_SLOT(Point_call, HPy_tp_call)
            static HPy
            Point_call_impl(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames)
            {
                long x, sum = 0;
                for (size_t i = 0; i < nargs; i++) {
                    x = HPyLong_AsLong(ctx, args[i]);
                    if (x == -1 && HPyErr_Occurred(ctx))
                        return HPy_NULL;
                    sum += x;
                }
                if (!HPy_IsNull(kwnames)) {
                    x = 1;
                    HPy_ssize_t n = HPy_Length(ctx, kwnames);
                    HPy h_factor_str = HPyUnicode_FromString(ctx, "factor");
                    HPy kwname;
                    for (HPy_ssize_t i=0; i < n; i++) {
                        kwname = HPy_GetItem_i(ctx, kwnames, i);
                        if (HPy_IsNull(kwname)) {
                            HPy_Close(ctx, h_factor_str);
                            return HPy_NULL;
                        }
                        if (HPy_RichCompareBool(ctx, h_factor_str, kwname, HPy_EQ)) {
                            x = HPyLong_AsLong(ctx, args[nargs + i]);
                            if (x == -1 && HPyErr_Occurred(ctx)) {
                                HPy_Close(ctx, kwname);
                                HPy_Close(ctx, h_factor_str);
                                return HPy_NULL;
                            }
                            HPy_Close(ctx, kwname);
                            break;
                        }
                        HPy_Close(ctx, kwname);
                    }
                    HPy_Close(ctx, h_factor_str);
                }
                PointObject *data = PointObject_AsStruct(ctx, callable);
                sum += data->x + data->y;
                return HPyLong_FromLong(ctx, sum * x);
            }
        """

    def EXPORT_POINT_TYPE(self, *defines):
        defines += ('NULL',)
        defines = ', '.join(defines)
        self.EXPORT_TYPE('"Point"', "Point_spec")
        return """
            static HPyDef *Point_defines[] = { %s };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .defines = Point_defines
            };
        """ % defines


    def METACLASS_STRUCT_BEGIN(self, struct_name):
        assert self._CURRENT_STRUCT is None
        self._CURRENT_STRUCT = struct_name
        return self._METACLASS_STRUCT_BEGIN_FORMAT.format(struct_name=struct_name)

    def METACLASS_STRUCT_END(self):
        assert self._CURRENT_STRUCT is not None
        struct_name = self._CURRENT_STRUCT
        self._CURRENT_STRUCT = None
        return self._METACLASS_STRUCT_END_FORMAT.format(struct_name=struct_name)

    def DEFINE_DummyMeta_struct(self):
        type_begin = self.METACLASS_STRUCT_BEGIN("DummyMeta")
        type_end = self.METACLASS_STRUCT_END()
        return """
            {type_begin}
                int meta_magic;
                int meta_member;
                char some_more[64];
            {type_end}
        """.format(type_begin=type_begin, type_end=type_end)

    def DEFINE_DummyMeta(self):
        struct = self.DEFINE_DummyMeta_struct()
        return """
            {struct}

            static HPyType_Spec DummyMeta_spec = {{
                .name = "mytest.DummyMeta",
                .basicsize = sizeof(DummyMeta),
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                .builtin_shape = SHAPE(DummyMeta),
            }};

            static HPy make_DummyMeta(HPyContext *ctx)
            {{
                HPyType_SpecParam param[] = {{
                    {{ HPyType_SpecParam_Base, ctx->h_TypeType }},
                    {{ (HPyType_SpecParam_Kind)0 }}
                }};
                return HPyType_FromSpec(ctx, &DummyMeta_spec, param);
            }}
        """.format(struct=struct)

    def EXPORT_DummyMeta(self):
        self.EXTRA_INIT_FUNC("register_DummyMeta")
        return """
            static void register_DummyMeta(HPyContext *ctx, HPy module)
            {
                HPy h_DummyMeta = make_DummyMeta(ctx);
                if (HPy_IsNull(h_DummyMeta))
                    return;
                HPy_SetAttr_s(ctx, module, "DummyMeta", h_DummyMeta);
                HPy_Close(ctx, h_DummyMeta);
            }
        """

    def DEFINE_Dummy_struct(self):
        type_begin = self.TYPE_STRUCT_BEGIN("Dummy")
        type_end = self.TYPE_STRUCT_END()
        return """
            {type_begin}
                int member;
            {type_end}
            """.format(type_begin=type_begin, type_end=type_end)

    def DEFINE_Dummy(self):
        struct = self.DEFINE_Dummy_struct()
        return """
            {struct}

            HPyDef_MEMBER(member, "member", HPyMember_INT, offsetof(Dummy, member))

            static HPyDef *Dummy_defines[] = {{
                &member,
                NULL
            }};

            static HPyType_Spec Dummy_spec = {{
                .name = "mytest.Dummy",
                .basicsize = sizeof(Dummy),
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                .builtin_shape = SHAPE(Dummy),
                .defines = Dummy_defines,
            }};
            """.format(struct=struct)

    def DEFINE_meta_data_accessors(self):
        return """
            HPyDef_METH(set_meta_data, "set_meta_data", HPyFunc_O)
            static HPy set_meta_data_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                DummyMeta *data = DummyMeta_AsStruct(ctx, arg);
                data->meta_magic = 42;
                data->meta_member = 11;
                for (size_t i = 0; i < 64; ++i)
                    data->some_more[i] = (char) i;
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(get_meta_data, "get_meta_data", HPyFunc_O)
            static HPy get_meta_data_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                DummyMeta *data = DummyMeta_AsStruct(ctx, arg);
                for (size_t i = 0; i < 64; ++i) {
                    if (data->some_more[i] != (char) i) {
                        HPyErr_SetString(ctx, ctx->h_RuntimeError, "some_more got mangled");
                        return HPy_NULL;
                    }
                }
                return HPyLong_FromLong(ctx, data->meta_magic + data->meta_member);
            }

            HPyDef_METH(set_member, "set_member", HPyFunc_O)
            static HPy set_member_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                Dummy *data = Dummy_AsStruct(ctx, arg);
                data->member = 123614;
                return HPy_Dup(ctx, ctx->h_None);
            }
            """


class TestType(HPyTest):

    ExtensionTemplate = PointTemplate

    def test_simple_type(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                @DEFAULT_SHAPE
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
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                @DEFAULT_SHAPE
                .doc = "A succinct description.",
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        assert mod.Dummy.__doc__ == "A succinct description."

    def test_HPyDef_SLOT_IMPL(self):
        mod = self.make_module("""
            HPyDef_SLOT_IMPL(Dummy_repr, Dummy_repr_impl, HPy_tp_repr);
            static HPy Dummy_repr_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "<Dummy>");
            }

            HPyDef_SLOT_IMPL(Dummy_abs, Dummy_abs_impl, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext *ctx, HPy self)
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
                @DEFAULT_SHAPE
                .defines = Dummy_defines,
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert repr(d) == '<Dummy>'
        assert abs(d) == 1234

    def test_HPyDef_SLOT(self):
        mod = self.make_module("""
            HPyDef_SLOT(Dummy_repr, HPy_tp_repr);
            static HPy Dummy_repr_impl(HPyContext *ctx, HPy self)
            {
                return HPyUnicode_FromString(ctx, "<Dummy>");
            }

            HPyDef_SLOT(Dummy_abs, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext *ctx, HPy self)
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
                .defines = Dummy_defines,
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert repr(d) == '<Dummy>'
        assert abs(d) == 1234

    def test_HPyDef_METH_IMPL(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH_IMPL(Dummy_foo, "foo", Dummy_foo_impl, HPyFunc_O, .doc="hello")
            static HPy Dummy_foo_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Add(ctx, arg, arg);
            }

            HPyDef_METH_IMPL(Dummy_bar, "bar", Dummy_bar_impl, HPyFunc_NOARGS)
            static HPy Dummy_bar_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            HPyDef_METH_IMPL(Dummy_identity, "identity", Dummy_identity_impl, HPyFunc_NOARGS)
            static HPy Dummy_identity_impl(HPyContext *ctx, HPy self)
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
                .defines = dummy_type_defines,
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

    def test_HPyDef_METH(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(Dummy_foo, "foo", HPyFunc_O, .doc="hello")
            static HPy Dummy_foo_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_Add(ctx, arg, arg);
            }

            HPyDef_METH(Dummy_bar, "bar", HPyFunc_NOARGS)
            static HPy Dummy_bar_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            HPyDef_METH(Dummy_identity, "identity", HPyFunc_NOARGS)
            static HPy Dummy_identity_impl(HPyContext *ctx, HPy self)
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
                @DEFAULT_SHAPE
                .defines = dummy_type_defines,
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

            HPyDef_METH(Point_foo, "foo", HPyFunc_NOARGS)
            static HPy Point_foo_impl(HPyContext *ctx, HPy self)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_foo)
            @INIT
        """)
        p1 = mod.Point(7, 3)
        assert p1.foo() == 73
        p2 = mod.Point(4, 2)
        assert p2.foo() == 42

    def test_HPy_New_initialize_to_zero(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_xy

            HPyDef_METH(newPoint, "newPoint", HPyFunc_NOARGS)
            static HPy newPoint_impl(HPyContext *ctx, HPy self)
            {
                HPy h_pointClass = HPy_GetAttr_s(ctx, self, "Point");
                if (HPy_IsNull(h_pointClass))
                    return HPy_NULL;

                PointObject *point;
                HPy h_point = HPy_New(ctx, h_pointClass, &point);
                HPy_Close(ctx, h_pointClass);
                return h_point;
            }

            @EXPORT(newPoint)
            @EXPORT_POINT_TYPE(&Point_x, &Point_y)
            @INIT
        """)
        # this is suboptimal: if we don't initialized the memory after
        # allocation, it might be 0 anyway. Try to allocate several Points to
        # increase the chances that the test don't pass by chance
        for i in range(10):
            p = mod.newPoint()
            assert p.x == 0
            assert p.y == 0

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
            @TYPE_STRUCT_BEGIN(FooObject)
                %(c_type)s member;
            @TYPE_STRUCT_END

            HPyDef_SLOT(Foo_new, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
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
                .builtin_shape = SHAPE(FooObject),
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
            @TYPE_STRUCT_BEGIN(FooObject)
                %(c_type)s member;
            @TYPE_STRUCT_END

            HPyDef_SLOT(Foo_new, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
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
                .builtin_shape = SHAPE(FooObject),
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
            @TYPE_STRUCT_BEGIN(FooObject)
                float FLOAT_member;
                double DOUBLE_member;
                const char* STRING_member;
                const char *STRING_null_member;
                char CHAR_member;
                char ISTRING_member[6];
                char BOOL_member;
                HPyField OBJECT_member;
                HPyField OBJECT_NULL_member;
                HPyField OBJECT_EX_member;
            @TYPE_STRUCT_END

            HPyDef_SLOT(Foo_new, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
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
                HPyField_Store(ctx, h_obj, &foo->OBJECT_member, ctx->h_NotImplemented);
                foo->OBJECT_NULL_member = HPyField_NULL;
                foo->OBJECT_EX_member = HPyField_NULL;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_FLOAT_member, "FLOAT_member", HPyMember_FLOAT, offsetof(FooObject, FLOAT_member))
            HPyDef_MEMBER(Foo_DOUBLE_member, "DOUBLE_member", HPyMember_DOUBLE, offsetof(FooObject, DOUBLE_member))
            HPyDef_MEMBER(Foo_STRING_member, "STRING_member", HPyMember_STRING, offsetof(FooObject, STRING_member))
            HPyDef_MEMBER(Foo_STRING_null_member, "STRING_null_member", HPyMember_STRING, offsetof(FooObject, STRING_null_member))
            HPyDef_MEMBER(Foo_CHAR_member, "CHAR_member", HPyMember_CHAR, offsetof(FooObject, CHAR_member))
            HPyDef_MEMBER(Foo_ISTRING_member, "ISTRING_member", HPyMember_STRING_INPLACE, offsetof(FooObject, ISTRING_member))
            HPyDef_MEMBER(Foo_BOOL_member, "BOOL_member", HPyMember_BOOL, offsetof(FooObject, BOOL_member))
            HPyDef_MEMBER(Foo_OBJECT_member, "OBJECT_member", HPyMember_OBJECT, offsetof(FooObject, OBJECT_member))
            HPyDef_MEMBER(Foo_OBJECT_NULL_member, "OBJECT_NULL_member", HPyMember_OBJECT, offsetof(FooObject, OBJECT_NULL_member))
            HPyDef_MEMBER(Foo_OBJECT_EX_member, "OBJECT_EX_member", HPyMember_OBJECT_EX, offsetof(FooObject, OBJECT_EX_member))
            HPyDef_MEMBER(Foo_NONE_member, "NONE_member", HPyMember_NONE, offsetof(FooObject, FLOAT_member))

            HPyDef_SLOT(Foo_traverse, HPy_tp_traverse)
            static int Foo_traverse_impl(void *self, HPyFunc_visitproc visit, void *arg)
            {
                FooObject *p = (FooObject *)self;
                HPy_VISIT(&p->OBJECT_member);
                HPy_VISIT(&p->OBJECT_NULL_member);
                HPy_VISIT(&p->OBJECT_EX_member);
                return 0;
            }

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_FLOAT_member,
                    &Foo_DOUBLE_member,
                    &Foo_STRING_member,
                    &Foo_STRING_null_member,
                    &Foo_CHAR_member,
                    &Foo_ISTRING_member,
                    &Foo_BOOL_member,
                    &Foo_OBJECT_member,
                    &Foo_OBJECT_NULL_member,
                    &Foo_OBJECT_EX_member,
                    &Foo_NONE_member,
                    &Foo_traverse,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "mytest.Foo",
                .basicsize = sizeof(FooObject),
                .builtin_shape = SHAPE(FooObject),
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

        assert foo.OBJECT_member is NotImplemented
        foo.OBJECT_member = 1
        assert foo.OBJECT_member == 1

        assert foo.OBJECT_NULL_member is None
        foo.OBJECT_NULL_member = 1
        assert foo.OBJECT_NULL_member == 1
        del foo.OBJECT_NULL_member
        assert foo.OBJECT_NULL_member is None

        with pytest.raises(AttributeError, match="OBJECT_EX_member"):
            foo.OBJECT_EX_member
        foo.OBJECT_EX_member = 1
        assert foo.OBJECT_EX_member == 1
        del foo.OBJECT_EX_member
        with pytest.raises(AttributeError):
            foo.OBJECT_EX_member

        assert foo.NONE_member is None
        with pytest.raises((SystemError, TypeError)):  # CPython quirk/bug
            foo.NONE_member = None
        with pytest.raises(TypeError):
            del foo.NONE_member

    def test_HPyDef_Member_readonly_others(self):
        import pytest
        mod = self.make_module("""
            #include <string.h>
            @TYPE_STRUCT_BEGIN(FooObject)
                float FLOAT_member;
                double DOUBLE_member;
                const char* STRING_member;
                char CHAR_member;
                char ISTRING_member[6];
                char BOOL_member;
                HPyField OBJECT_member;
            @TYPE_STRUCT_END

            HPyDef_SLOT(Foo_new, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
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
                foo->OBJECT_member = HPyField_NULL;
                return h_obj;
            }

            HPyDef_MEMBER(Foo_FLOAT_member, "FLOAT_member", HPyMember_FLOAT, offsetof(FooObject, FLOAT_member), .readonly=1)
            HPyDef_MEMBER(Foo_DOUBLE_member, "DOUBLE_member", HPyMember_DOUBLE, offsetof(FooObject, DOUBLE_member), .readonly=1)
            HPyDef_MEMBER(Foo_STRING_member, "STRING_member", HPyMember_STRING, offsetof(FooObject, STRING_member), .readonly=1)
            HPyDef_MEMBER(Foo_CHAR_member, "CHAR_member", HPyMember_CHAR, offsetof(FooObject, CHAR_member), .readonly=1)
            HPyDef_MEMBER(Foo_ISTRING_member, "ISTRING_member", HPyMember_STRING_INPLACE, offsetof(FooObject, ISTRING_member), .readonly=1)
            HPyDef_MEMBER(Foo_BOOL_member, "BOOL_member", HPyMember_BOOL, offsetof(FooObject, BOOL_member), .readonly=1)
            HPyDef_MEMBER(Foo_OBJECT_member, "OBJECT_member", HPyMember_OBJECT, offsetof(FooObject, OBJECT_member), .readonly=1)
            HPyDef_MEMBER(Foo_NONE_member, "NONE_member", HPyMember_NONE, offsetof(FooObject, FLOAT_member), .readonly=1)

            HPyDef_SLOT(Foo_traverse, HPy_tp_traverse)
            static int Foo_traverse_impl(void *self, HPyFunc_visitproc visit, void *arg)
            {
                FooObject *p = (FooObject *)self;
                HPy_VISIT(&p->OBJECT_member);
                return 0;
            }

            static HPyDef *Foo_defines[] = {
                    &Foo_new,
                    &Foo_FLOAT_member,
                    &Foo_DOUBLE_member,
                    &Foo_STRING_member,
                    &Foo_CHAR_member,
                    &Foo_ISTRING_member,
                    &Foo_BOOL_member,
                    &Foo_OBJECT_member,
                    &Foo_NONE_member,
                    &Foo_traverse,
                    NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "mytest.Foo",
                .basicsize = sizeof(FooObject),
                .builtin_shape = SHAPE(FooObject),
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

        assert foo.OBJECT_member is None
        with pytest.raises(AttributeError):
            foo.OBJECT_member = 1
        with pytest.raises(AttributeError):
            del foo.OBJECT_member

        assert foo.NONE_member is None
        with pytest.raises(AttributeError):
            foo.NONE_member = None
        with pytest.raises(AttributeError):
            del foo.NONE_member

    def test_call(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_call

            HPyDef_SLOT(Dummy_call, HPy_tp_call)
            static HPy
            Dummy_call_impl(HPyContext *ctx, HPy callable, const HPy *args,
                            size_t nargs, HPy kwnames)
            {
                return HPyUnicode_FromString(ctx, "hello");
            }

            @EXPORT_POINT_TYPE(&Point_call)
            @INIT
        """)
        p = mod.Point()
        assert p(3, 4, 5, factor=2) == 24

    def test_call_with_tp_new(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new
            @DEFINE_Point_call
            @EXPORT_POINT_TYPE(&Point_new, &Point_call)
            @INIT
        """)
        p = mod.Point(1, 2)
        assert p(3, 4, 5, factor=2) == 30

    def test_call_set(self):
        import pytest
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_call

            HPyDef_CALL_FUNCTION(Point_special_call)
            static HPy
            Point_special_call_impl(HPyContext *ctx, HPy callable,
                                    const HPy *args, size_t nargs, HPy kwnames)
            {
                HPy tmp = Point_call_impl(ctx, callable, args, nargs, kwnames);
                HPy res = HPy_Negative(ctx, tmp);
                HPy_Close(ctx, tmp);
                return res;
            }

            HPyDef_SLOT(Point_new, HPy_tp_new)
            static HPy Point_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                long x, y;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "ll", &x, &y))
                    return HPy_NULL;
                PointObject *point;
                HPy h_point = HPy_New(ctx, cls, &point);
                if (HPy_IsNull(h_point))
                    return HPy_NULL;
                if (x < 0 && HPy_SetCallFunction(ctx, h_point, &Point_special_call) < 0) {
                    HPy_Close(ctx, h_point);
                    return HPy_NULL;
                }
                point->x = x;
                point->y = y;
                return h_point;
            }

            HPyDef_METH(call_set, "call_set", HPyFunc_O)
            static HPy call_set_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                if (HPy_SetCallFunction(ctx, arg, &Point_special_call) < 0)
                    return HPy_NULL;
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_call)
            @EXPORT(call_set)
            @INIT
        """)

        # this uses 'Point_call'
        p0 = mod.Point(1, 2)
        assert p0(3, 4, 5, factor=2) == 30

        # the negative 'x' will cause that 'Point_special_call' is used
        p1 = mod.Point(-1, 2)
        assert p1(3, 4, 5, factor=2) == -26

        # error case: setting call function on object that does not implement
        # the HPy call protocol
        with pytest.raises(TypeError):
            mod.call_set(object())

    def test_call_invalid_specs(self):
        import pytest
        mod = self.make_module("""
            HPyDef_SLOT(Dummy_call, HPy_tp_call)
            static HPy
            Dummy_call_impl(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames)
            {
                return HPyUnicode_FromString(ctx, "hello");
            }

            HPyDef_MEMBER(Dummy_vcall_offset, "__vectorcalloffset__", HPyMember_HPYSSIZET, 4*sizeof(void*), .readonly=1)

            static HPyDef *Dummy_defines[] = { &Dummy_call, NULL };
            static HPyDef *Dummy_vcall_defines[] = { &Dummy_call, &Dummy_vcall_offset, NULL };

            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = sizeof(intptr_t),
                .flags = HPy_TPFLAGS_DEFAULT,
                @DEFAULT_SHAPE
                .defines = Dummy_defines,
            };

            static HPyType_Spec Dummy_vcall_spec = {
                .name = "mytest.DummyVCall",
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_HAVE_VECTORCALL,
                @DEFAULT_SHAPE
                .defines = Dummy_vcall_defines,
            };

            HPyDef_METH(create_var_type, "create_var_type", HPyFunc_NOARGS)
            static HPy create_var_type_impl(HPyContext *ctx, HPy self)
            {
                if (!HPyHelpers_AddType(ctx, self, "Dummy", &Dummy_spec, NULL)) {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            HPyDef_METH(create_vcall, "create_call_and_vectorcalloffset_type", HPyFunc_NOARGS)
            static HPy create_vcall_impl(HPyContext *ctx, HPy self)
            {
                if (!HPyHelpers_AddType(ctx, self, "DummyVCall", &Dummy_vcall_spec, NULL)) {
                    return HPy_NULL;
                }
                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT(create_var_type)
            @EXPORT(create_vcall)
            @INIT
        """)
        with pytest.raises(TypeError):
            mod.create_var_type()
        with pytest.raises(TypeError):
            mod.create_call_and_vectorcalloffset_type()

    def test_call_explicit_offset(self):
        mod = self.make_module("""
            @TYPE_STRUCT_BEGIN(FooObject)
                void *a;
                HPyCallFunction call_func;
                void *b;
            @TYPE_STRUCT_END

            HPyDef_MEMBER(Foo_vcall_offset, "__vectorcalloffset__", HPyMember_HPYSSIZET, offsetof(FooObject, call_func), .readonly=1)

            HPyDef_CALL_FUNCTION(Foo_manual_call_func)
            static HPy
            Foo_manual_call_func_impl(HPyContext *ctx, HPy callable, const HPy *args, size_t nargs, HPy kwnames)
            {
                return HPyUnicode_FromString(ctx, "hello manually initialized call function");
            }

            HPyDef_SLOT(Foo_new, HPy_tp_new)
            static HPy Foo_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
                                    HPy_ssize_t nargs, HPy kw)
            {
                FooObject *data;
                HPy h_obj = HPy_New(ctx, cls, &data);
                if (HPy_IsNull(h_obj))
                    return HPy_NULL;
                data->call_func = Foo_manual_call_func;
                return h_obj;
            }

            static HPyDef *Foo_defines[] = {
                &Foo_vcall_offset,
                &Foo_new,
                NULL
            };

            static HPyType_Spec Foo_spec = {
                .name = "mytest.Foo",
                .basicsize = sizeof(FooObject),
                .itemsize = sizeof(intptr_t),
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_HAVE_VECTORCALL,
                @DEFAULT_SHAPE
                .defines = Foo_defines,
            };

            @EXPORT_TYPE("Foo", Foo_spec)
            @INIT
        """)
        foo = mod.Foo()
        assert foo() == 'hello manually initialized call function'

    def test_HPyType_GenericNew(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_xy

            HPyDef_SLOT_IMPL(Point_new, HPyType_GenericNew, HPy_tp_new)

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

            HPyDef_GET(Point_z, "z")
            static HPy Point_z_get(HPyContext *ctx, HPy self, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
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

            HPyDef_GETSET(Point_z, "z", .closure=(void *)1000)
            static HPy Point_z_get(HPyContext *ctx, HPy self, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y + (long)(HPy_ssize_t)closure);
            }
            static int Point_z_set(HPyContext *ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                long current = point->x*10 + point->y + (long)(HPy_ssize_t)closure;
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

            HPyDef_SET(Point_z, "z", .closure=(void *)1000)
            static int Point_z_set(HPyContext *ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                long current = point->x*10 + point->y + (long)(HPy_ssize_t)closure;
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

    def test_HPyDef_GET_IMPL(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_GET_IMPL(Point_z, "z", Point_z_get)
            static HPy Point_z_get(HPyContext *ctx, HPy self, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y);
            }

            @EXPORT_POINT_TYPE(&Point_new, &Point_z)
            @INIT
        """)
        p = mod.Point(7, 3)
        assert p.z == 73

    def test_HPyDef_GETSET_IMPL(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new

            HPyDef_GETSET_IMPL(Point_z, "z", Point_z_get, Point_z_set, .closure=(void *)1000)
            static HPy Point_z_get(HPyContext *ctx, HPy self, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                return HPyLong_FromLong(ctx, point->x*10 + point->y + (long)(HPy_ssize_t)closure);
            }
            static int Point_z_set(HPyContext *ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                long current = point->x*10 + point->y + (long)(HPy_ssize_t)closure;
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

    def test_HPyDef_SET_IMPL(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_new
            @DEFINE_Point_xy

            HPyDef_SET_IMPL(Point_z, "z", Point_z_set, .closure=(void *)1000)
            static int Point_z_set(HPyContext *ctx, HPy self, HPy value, void *closure)
            {
                PointObject *point = PointObject_AsStruct(ctx, self);
                long current = point->x*10 + point->y + (long)(HPy_ssize_t)closure;
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
                @DEFAULT_SHAPE
            };

            static void make_Dummy(HPyContext *ctx, HPy module)
            {
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { (HPyType_SpecParam_Kind)0 }
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
                @DEFAULT_SHAPE
            };

            static void make_Dummy(HPyContext *ctx, HPy module)
            {
                HPy h_bases = HPyTuple_Pack(ctx, 1, ctx->h_LongType);
                if (HPy_IsNull(h_bases))
                    return;
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_BasesTuple, h_bases },
                    { (HPyType_SpecParam_Kind)0 }
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

    def test_specparam_multiple_metaclass_fails(self):
        import pytest
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
            };

            HPyDef_METH(make_dummy, "make_dummy", HPyFunc_NOARGS)
            static HPy make_dummy_impl(HPyContext *ctx, HPy module)
            {
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Metaclass, ctx->h_TypeType },
                    { HPyType_SpecParam_Metaclass, ctx->h_LongType },
                    { (HPyType_SpecParam_Kind)0 }
                };
                return HPyType_FromSpec(ctx, &Dummy_spec, param);
            }
            @EXPORT(make_dummy)
            @INIT
        """)

        with pytest.raises(ValueError):
            mod.make_dummy()

    def test_metaclass(self):
        import pytest
        mod = self.make_module("""
            #include <string.h>

            @DEFINE_DummyMeta
            @DEFINE_Dummy
            @DEFINE_meta_data_accessors

            HPyDef_METH(create_type, "create_type", HPyFunc_VARARGS)
            static HPy create_type_impl(HPyContext *ctx, HPy module,
                                            const HPy *args, size_t nargs)
            {
                HPy metaclass;
                if (!HPyArg_Parse(ctx, NULL, args, nargs, "sO",
                        &Dummy_spec.name, &metaclass))
                    return HPy_NULL;

                HPyType_SpecParam specparam[] = {
                    { HPyType_SpecParam_Metaclass, metaclass },
                    { (HPyType_SpecParam_Kind)0 }
                };

                const char *bare_name = strrchr(Dummy_spec.name, '.');
                if (bare_name == NULL)
                    bare_name = Dummy_spec.name;
                else
                    bare_name++;

                if (!HPyHelpers_AddType(ctx, module, bare_name,
                                            &Dummy_spec, specparam))
                    return HPy_NULL;

                return HPy_Dup(ctx, ctx->h_None);
            }

            @EXPORT_DummyMeta
            @EXPORT(set_meta_data)
            @EXPORT(get_meta_data)
            @EXPORT(set_member)
            @EXPORT(create_type)
            @INIT
        """)

        assert type(mod.DummyMeta) is type
        mod.create_type("mytest.Dummy", mod.DummyMeta)
        assert mod.DummyMeta is type(mod.Dummy), "type(mod.Dummy) == %r" % (type(mod.Dummy), )
        assert isinstance(mod.Dummy, type)
        assert mod.set_meta_data(mod.Dummy) is None
        assert mod.get_meta_data(mod.Dummy) == 42 + 11

        d = mod.Dummy()
        mod.set_member(d)
        assert d.member == 123614

        # metaclasses must inherit from 'type'
        with pytest.raises(TypeError):
            mod.create_type("mytest.DummyFail0", "hello")

        class WithCustomNew:
            def __new__(self):
                print("hello")

        # types with custom 'tp_new' cannot be used as metaclass
        with pytest.raises(TypeError):
            mod.create_type("mytest.DummyFail1", WithCustomNew)

        # type 'int' also has a custom new
        with pytest.raises(TypeError):
            mod.create_type("mytest.DummyIntMeta", int)

    def test_get_name(self):
        import array
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .itemsize = 0,
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                @DEFAULT_SHAPE
            };

            HPyDef_METH(get_name, "get_name", HPyFunc_O)
            static HPy get_name_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                const char *name = HPyType_GetName(ctx, arg);
                if (name == NULL)
                    return HPy_NULL;
                return HPyUnicode_FromString(ctx, name);
            }

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @EXPORT(get_name)
            @INIT
        """)
        assert mod.Dummy.__name__ == "Dummy"
        assert mod.get_name(mod.Dummy) == "Dummy"
        assert mod.get_name(str) == "str"
        assert mod.get_name(array.array) == "array"

    def test_issubtype(self):
        mod = self.make_module("""
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                @DEFAULT_SHAPE
            };

            static HPyType_Spec Single_spec = {
                .name = "mytest.Single",
                @DEFAULT_SHAPE
            };

            static HPyType_Spec Dual_spec = {
                .name = "mytest.Dual",
                @DEFAULT_SHAPE
            };

            static void make_types(HPyContext *ctx, HPy module)
            {
                HPy h_dummy = HPyType_FromSpec(ctx, &Dummy_spec, NULL);
                HPy_SetAttr_s(ctx, module, "Dummy", h_dummy);
                HPyType_SpecParam single_param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { (HPyType_SpecParam_Kind)0 }
                };
                HPy h_single = HPyType_FromSpec(ctx, &Single_spec, single_param);
                if (HPy_IsNull(h_single))
                    return;
                HPy_SetAttr_s(ctx, module, "Single", h_single);
                HPy_Close(ctx, h_single);

                HPyType_SpecParam dual_param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { HPyType_SpecParam_Base, h_dummy },
                    { (HPyType_SpecParam_Kind)0 }
                };
                HPy h_dual = HPyType_FromSpec(ctx, &Dual_spec, dual_param);
                HPy_Close(ctx, h_dummy);
                if (HPy_IsNull(h_dual))
                    return;
                HPy_SetAttr_s(ctx, module, "Dual", h_dual);
                HPy_Close(ctx, h_dual);
            }

            HPyDef_METH(issubtype, "issubtype", HPyFunc_VARARGS)
            static HPy issubtype_impl(HPyContext *ctx, HPy self, const HPy *args, size_t nargs)
            {
                if (nargs != 2) {
                    HPyErr_SetString(ctx, ctx->h_TypeError, "expected exactly 2 arguments");
                    return HPy_NULL;
                }
                int res = HPyType_IsSubtype(ctx, args[0], args[1]);
                return HPyLong_FromLong(ctx, res);
            }

            @EXPORT(issubtype)
            @EXTRA_INIT_FUNC(make_types)
            @INIT
        """)

        class EveryMeta(type):
            def __subclasscheck__(self, subclass):
                return subclass is not None
        Every = EveryMeta('Every', (), {})
        assert mod.issubtype(mod.Single, int)
        assert mod.issubtype(mod.Dual, int)
        assert mod.issubtype(mod.Dual, mod.Dummy)
        assert not mod.issubtype(mod.Single, mod.Dummy)
        assert not mod.issubtype(mod.Single, mod.Dual)
        assert not mod.issubtype(mod.Dual, mod.Single)
        assert issubclass(mod.Single, Every)
        assert issubclass(mod.Dual, Every)
        assert not mod.issubtype(mod.Single, Every)
        assert not mod.issubtype(mod.Dual, Every)


class TestPureHPyType(HPyTest):

    ExtensionTemplate = PointTemplate

    def test_builtin_shape(self):
        mod = self.make_module("""
            @DEFINE_PointObject(HPyType_BuiltinShape_Long)
            @DEFINE_Point_xy

            static HPyDef *Point_defines[] = {
                &Point_x,
                &Point_y,
                NULL
            };

            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .defines = Point_defines
            };

            static void make_Point(HPyContext *ctx, HPy module)
            {
                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Base, ctx->h_LongType },
                    { (HPyType_SpecParam_Kind)0 }
                };
                HPy h_Point = HPyType_FromSpec(ctx, &Point_spec, param);
                if (HPy_IsNull(h_Point))
                    return;
                HPy_SetAttr_s(ctx, module, "Point", h_Point);
                HPy_Close(ctx, h_Point);
            }
            @EXTRA_INIT_FUNC(make_Point)
            @INIT
        """)
        assert isinstance(mod.Point, type)
        assert mod.Point.__name__ == 'Point'
        assert mod.Point.__module__ == 'mytest'
        assert issubclass(mod.Point, int)
        assert isinstance(mod.Point(), mod.Point)
        p0 = mod.Point()
        assert p0 == 0
        assert p0.x == 0
        assert p0.y == 0

        p42 = mod.Point(42)
        p42.x = 123
        p42.y = 456
        assert p42 == 42
        assert p42.x == 123
        assert p42.y == 456

    def test_invalid_shape(self):
        import pytest
        with pytest.raises(ValueError):
            self.make_module("""
                static HPyType_Spec Dummy_spec = {
                    .name = "mytest.Dummy",
                    .builtin_shape = (HPyType_BuiltinShape)123
                };

                @EXPORT_TYPE("Dummy", Dummy_spec)
                @INIT
            """)

    def test_call_zero_basicsize(self):
        mod = self.make_module("""
            HPyDef_SLOT(Dummy_call, HPy_tp_call)
            static HPy
            Dummy_call_impl(HPyContext *ctx, HPy callable, const HPy *args,
                            size_t nargs, HPy kwnames)
            {
                return HPyUnicode_FromString(ctx, "hello");
            }

            static HPyDef *Dummy_defines[] = { &Dummy_call, NULL };
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                @DEFAULT_SHAPE
                .defines = Dummy_defines,
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        # type 'Dummy' has basicsize == 0; this test ensures that installation
        # of the hidden call function field is done correctly
        q = mod.Dummy()
        assert q() == 'hello'
