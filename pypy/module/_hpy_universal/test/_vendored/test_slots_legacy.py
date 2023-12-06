""" HPyType slot tests on legacy types. """

from .support import HPyTest #, make_hpy_abi_fixture
from .test_hpytype_legacy import LegacyPointTemplate
from .test_slots import TestSlots as _TestSlots, TestSqSlots as _TestSqSlots

# hpy_abi = make_hpy_abi_fixture('with hybrid')

class TestLegacySlots(_TestSlots):
    ExtensionTemplate = LegacyPointTemplate
    USE_CPYEXT = True


class TestLegacySqSlots(_TestSqSlots):
    ExtensionTemplate = LegacyPointTemplate
    USE_CPYEXT = True


class TestCustomLegacySlotsFeatures(HPyTest):
    USE_CPYEXT = True

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

            HPyDef_SLOT(Dummy_abs, HPy_nb_absolute);
            static HPy Dummy_abs_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            static HPyDef *Dummy_defines[] = {
                &Dummy_abs,
                NULL
            };
            static PyType_Slot Dummy_type_slots[] = {
                {Py_tp_repr, (void*)Dummy_repr},
                {Py_nb_add, (void*)Dummy_add},
                {0, 0},
            };
            static HPyType_Spec Dummy_spec = {
                .name = "mytest.Dummy",
                .builtin_shape = HPyType_BuiltinShape_Legacy,
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

    def test_legacy_slots_methods(self):
        mod = self.make_module("""
            #include <Python.h>

            static PyObject *Dummy_foo(PyObject *self, PyObject *arg)
            {
                Py_INCREF(arg);
                return arg;
            }

            HPyDef_METH(Dummy_bar, "bar", HPyFunc_NOARGS)
            static HPy Dummy_bar_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, 1234);
            }

            static PyMethodDef dummy_methods[] = {
               {"foo", Dummy_foo, METH_O},
               {NULL, NULL}         /* Sentinel */
            };

            static PyType_Slot dummy_type_slots[] = {
                {Py_tp_methods, dummy_methods},
                {0, 0},
            };

            static HPyDef *dummy_type_defines[] = {
                    &Dummy_bar,
                    NULL
            };

            static HPyType_Spec dummy_type_spec = {
                .name = "mytest.Dummy",
                .builtin_shape = HPyType_BuiltinShape_Legacy,
                .legacy_slots = dummy_type_slots,
                .defines = dummy_type_defines
            };

            @EXPORT_TYPE("Dummy", dummy_type_spec)
            @INIT
        """)
        d = mod.Dummy()
        assert d.foo(21) == 21
        assert d.bar() == 1234

    def test_legacy_slots_members(self):
        import pytest
        mod = self.make_module("""
            #include <Python.h>
            #include "structmember.h"

            typedef struct {
                PyObject_HEAD
                long x;
                long y;
            } PointObject;

            HPyDef_SLOT(Point_new, HPy_tp_new)
            static HPy Point_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                PointObject *point;
                HPy h_point = HPy_New(ctx, cls, &point);
                if (HPy_IsNull(h_point))
                    return HPy_NULL;
                point->x = 7;
                point->y = 3;
                return h_point;
            }

            HPyDef_MEMBER(Point_x, "x", HPyMember_LONG, offsetof(PointObject, x))

            // legacy members
            static PyMemberDef legacy_members[] = {
                {"y", T_LONG, offsetof(PointObject, y), 0},
                {"y_ro", T_LONG, offsetof(PointObject, y), READONLY},
                {NULL}
            };

            static PyType_Slot legacy_slots[] = {
                {Py_tp_members, legacy_members},
                {0, NULL}
            };

            static HPyDef *Point_defines[] = {
                &Point_new,
                &Point_x,
                NULL
            };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = HPyType_BuiltinShape_Legacy,
                .legacy_slots = legacy_slots,
                .defines = Point_defines
            };

            @EXPORT_TYPE("Point", Point_spec)
            @INIT
        """)
        p = mod.Point()
        assert p.x == 7
        assert p.y == 3
        assert p.y_ro == 3
        p.x = 123
        p.y = 456
        with pytest.raises(AttributeError):
            p.y_ro = 789
        assert p.x == 123
        assert p.y == 456

    def test_legacy_slots_getsets(self):
        mod = self.make_module("""
            #include <Python.h>

            typedef struct {
                PyObject_HEAD
                long x;
                long y;
            } PointObject;

            HPyDef_SLOT(Point_new, HPy_tp_new)
            static HPy Point_new_impl(HPyContext *ctx, HPy cls, const HPy *args,
                                      HPy_ssize_t nargs, HPy kw)
            {
                PointObject *point;
                HPy h_point = HPy_New(ctx, cls, &point);
                if (HPy_IsNull(h_point))
                    return HPy_NULL;
                point->x = 7;
                point->y = 3;
                return h_point;
            }

            static PyObject *z_get(PointObject *point, void *closure)
            {
                long z = point->x*10 + point->y + (long)(HPy_ssize_t)closure;
                return PyLong_FromLong(z);
            }

            // legacy getsets
            static PyGetSetDef legacy_getsets[] = {
                {"z", (getter)z_get, NULL, NULL, (void *)2000},
                {NULL}
            };

            static PyType_Slot legacy_slots[] = {
                {Py_tp_getset, legacy_getsets},
                {0, NULL}
            };

            static HPyDef *Point_defines[] = {
                &Point_new,
                NULL
            };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = HPyType_BuiltinShape_Legacy,
                .legacy_slots = legacy_slots,
                .defines = Point_defines
            };

            HPyDef_METH(get_z, "get_z", HPyFunc_O)
            static HPy get_z_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                return HPy_GetAttr_s(ctx, arg, "z");
            }

            @EXPORT_TYPE("Point", Point_spec)
            @EXPORT(get_z)
            @INIT
        """)
        p = mod.Point()
        assert p.z == 2073
        assert mod.get_z(p) == 2073

    def test_legacy_slots_fails_without_legacy(self):
        import pytest
        mod_src = """
            #include <Python.h>

            static PyObject *Dummy_foo(PyObject *self, PyObject *arg)
            {
                Py_INCREF(arg);
                return arg;
            }

            static PyMethodDef dummy_methods[] = {
               {"foo", Dummy_foo, METH_O},
               {NULL, NULL}         /* Sentinel */
            };

            static PyType_Slot dummy_type_slots[] = {
                {Py_tp_methods, dummy_methods},
                {0, 0},
            };

            static HPyType_Spec dummy_type_spec = {
                .name = "mytest.Dummy",
                .builtin_shape = HPyType_BuiltinShape_Object,
                .legacy_slots = dummy_type_slots,
            };

            @EXPORT_TYPE("Dummy", dummy_type_spec)
            @INIT
        """
        with pytest.raises(TypeError) as err:
            self.make_module(mod_src)
        assert str(err.value) == (
            "cannot specify .legacy_slots without setting .builtin_shape=HPyType_BuiltinShape_Legacy")

    def test_buffer_legacy(self):
        # Copy the code from non-legacy test_buffer, and use the C-API interfaces
        # make sure C-level gets the HPy-level bf_getbuffer function
        mod = self.make_module("""
            #include <Python.h>
            typedef struct {
                PyObject_HEAD
                int exports;
            } FakeArrayObject;

            HPyType_LEGACY_HELPERS(FakeArrayObject);

            static char static_mem[12] = {0,1,2,3,4,5,6,7,8,9,10,11};
            static HPy_ssize_t _shape[1] = {12};
            static HPy_ssize_t _strides[1] = {1};

            HPyDef_SLOT_IMPL(FakeArray_getbuffer, _getbuffer_impl, HPy_bf_getbuffer)
            static int _getbuffer_impl(HPyContext *ctx, HPy self, HPy_buffer* buf, int flags) {
                FakeArrayObject *arr = FakeArrayObject_AsStruct(ctx, self);
                if (arr->exports > 0) {
                    buf->obj = HPy_NULL;
                    HPyErr_SetString(ctx, ctx->h_BufferError,
                               "only one buffer allowed");
                    return -1;
                }
                arr->exports++;
                buf->buf = static_mem;
                buf->len = 12;
                buf->itemsize = 1;
                buf->readonly = 1;
                buf->ndim = 1;
                buf->format = (char*)"B";
                buf->shape = _shape;
                buf->strides = _strides;
                buf->suboffsets = NULL;
                buf->internal = NULL;
                buf->obj = HPy_Dup(ctx, self);
                return 0;
            }

            HPyDef_SLOT_IMPL(FakeArray_releasebuffer, _relbuffer_impl, HPy_bf_releasebuffer)
            static void _relbuffer_impl(HPyContext *ctx, HPy h_obj, HPy_buffer* buf) {
                FakeArrayObject *arr = FakeArrayObject_AsStruct(ctx, h_obj);
                arr->exports--;
            }

            static HPyDef *FakeArray_defines[] = {
                &FakeArray_getbuffer,
                &FakeArray_releasebuffer,
                NULL
            };

            static HPyType_Spec FakeArray_Spec = {
                .name = "mytest.FakeArray",
                .basicsize = sizeof(FakeArrayObject),
                .builtin_shape = SHAPE(FakeArrayObject),
                .defines = FakeArray_defines,
            };

            HPyDef_METH(pybuffer, "pybuffer", HPyFunc_O)
            static HPy pybuffer_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                Py_buffer view;
                PyObject *o = HPy_AsPyObject(ctx, arg);
                size_t hasbuffer = PyObject_CheckBuffer(o);
                if (!hasbuffer) {
                    Py_DecRef(o);
                    HPyErr_SetString(ctx, ctx->h_RuntimeError, "PyObject_CheckBuffer failed");
                    return HPy_NULL;
                }
                if (PyObject_GetBuffer(o, &view, PyBUF_SIMPLE) != 0) {
                    Py_DecRef(o);
                    return HPy_NULL;
                }
                PyBuffer_Release(&view);
                return HPyLong_FromLong(ctx, 0);
            }

            @EXPORT(pybuffer)
            @EXPORT_TYPE("FakeArray", FakeArray_Spec)
            @INIT
        """)
        arr = mod.FakeArray()
        assert mod.pybuffer(arr) == 0
