"""
This file contains extra hpy tests in addition to the ones which are in
test/_vendored.

The idea is that during development, sometimes it is useful to write tests
about certain specific features/code paths/corner cases which are not covered
(yet!) by the official hpy tests, so this is a place to collect them.

Once the development phase is finished, please move these tests to the main
hpy repo, and then copy them back here via ./update_vendored.sh.
"""

from pypy.module._hpy_universal.test._vendored.support import HPyTest

class TestExtra(HPyTest):
    pass

    """
    Additional tests to write:

      - check the .readonly field of HPyDef_MEMBER (and also the corresponding
        flag for the PyMemberDef cpy_compat case)


    ListBuilder:

      - in the C code there is logic to delay the MemoryError until we call
        ListBuilder_Build, but it is not tested

      - ListBuilder_Cancel is not tested

    """

    # this is an update for the already-existing test in test_hpytype.py 
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



class TestExtraCPythonCompatibility(HPyTest):
    # these tests are run with cpyext support, see conftest.py

    # this is like the original test_legacy_slots_repr, but it also tests
    # nb_add (which is interesting since it's another function type, and it's
    # not a 'direct' tp_* slot but it's inside PyNumberMethods
    def test_legacy_slots(self):
        mod = self.make_module("""
            #include <Python.h>

            static PyObject *Dummy_repr(PyObject *self)
            {
                return PyUnicode_FromString("myrepr");
            }

            static PyObject *Dummy_add(PyObject *self, PyObject *other)
            {
                return Py_BuildValue("OO", self, other);
            }

            HPyDef_SLOT(Dummy_abs, Dummy_abs_impl, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            static HPyDef *Dummy_defines[] = {
                &Dummy_abs,
                NULL
            };
            static PyType_Slot Dummy_type_slots[] = {
                {Py_tp_repr, Dummy_repr},
                {Py_nb_add, Dummy_add},
                {0, 0},
            };
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .legacy_slots = Dummy_type_slots,
                .defines = Dummy_defines
            };

            @EXPORT_TYPE("Dummy", Dummy_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert repr(d) == 'myrepr'
        assert d + 42 == (d, 42)
        assert abs(d) == 1234
