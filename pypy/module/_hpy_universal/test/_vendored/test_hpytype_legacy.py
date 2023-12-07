""" HPyType tests on legacy types. """

import pytest
from .support import HPyTest #, make_hpy_abi_fixture
from .test_hpytype import PointTemplate, TestType as _TestType

# hpy_abi = make_hpy_abi_fixture('with hybrid')

class LegacyPointTemplate(PointTemplate):
    """
    Override PointTemplate to instead define a legacy point type that
    still provides access to PyObject_HEAD.
    """

    _STRUCT_BEGIN_FORMAT = """
        #include <Python.h>
        typedef struct {{
            PyObject_HEAD
    """

    _STRUCT_END_FORMAT = """
        }} {struct_name};
        HPyType_LEGACY_HELPERS({struct_name})
    """

    _METACLASS_STRUCT_BEGIN_FORMAT = """
        #include <Python.h>
        typedef struct {{
            PyHeapTypeObject super;
    """

    _METACLASS_STRUCT_END_FORMAT = _STRUCT_END_FORMAT

    def DEFAULT_SHAPE(self):
        return ".builtin_shape = HPyType_BuiltinShape_Legacy,"


class TestLegacyType(_TestType):

    ExtensionTemplate = LegacyPointTemplate
    USE_CPYEXT = True

    @pytest.mark.syncgc
    def test_legacy_dealloc(self):
        mod = self.make_module("""
            static long dealloc_counter = 0;

            HPyDef_METH(get_counter, "get_counter", HPyFunc_NOARGS)
            static HPy get_counter_impl(HPyContext *ctx, HPy self)
            {
                return HPyLong_FromLong(ctx, dealloc_counter);
            }

            @DEFINE_PointObject
            @DEFINE_Point_new
            static void Point_dealloc(PyObject *self)
            {
                dealloc_counter++;
                Py_TYPE(self)->tp_free(self);
            }

            static HPyDef *Point_defines[] = {&Point_new, NULL};
            static PyType_Slot Point_slots[] = {
                {Py_tp_dealloc, (void*)Point_dealloc},
                {0, NULL},
            };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .legacy_slots = Point_slots,
                .defines = Point_defines,
            };

            @EXPORT(get_counter)
            @EXPORT_TYPE("Point", Point_spec)
            @INIT
        """)
        assert mod.get_counter() == 0
        p = mod.Point(0, 0)
        del p
        self.debug_collect()
        assert mod.get_counter() == 1

    def test_legacy_dealloc_and_HPy_tp_traverse(self):
        import pytest
        mod_src = """
            @DEFINE_PointObject
            @DEFINE_Point_new
            HPyDef_SLOT(Point_traverse, HPy_tp_traverse)
            static int Point_traverse_impl(void *self, HPyFunc_visitproc visit, void *arg)
            {
                return 0;
            }
            static void Point_dealloc(PyObject *self)
            {
                return;
            }

            static HPyDef *Point_defines[] = {&Point_new, &Point_traverse, NULL};
            static PyType_Slot Point_slots[] = {
                {Py_tp_dealloc, (void*)Point_dealloc},
                {0, NULL},
            };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .legacy_slots = Point_slots,
                .defines = Point_defines,
            };
            @EXPORT_TYPE("Point", Point_spec)
            @INIT
        """
        with pytest.raises(TypeError) as err:
            mod = self.make_module(mod_src)
        assert "legacy tp_dealloc" in str(err.value)

    def test_legacy_dealloc_and_HPy_tp_destroy(self):
        import pytest
        mod_src = """
            @DEFINE_PointObject
            @DEFINE_Point_new
            HPyDef_SLOT(Point_destroy, HPy_tp_destroy)
            static void Point_destroy_impl(void *obj)
            {
                return;
            }
            static void Point_dealloc(PyObject *self)
            {
                return;
            }

            static HPyDef *Point_defines[] = {&Point_new, &Point_destroy, NULL};
            static PyType_Slot Point_slots[] = {
                {Py_tp_dealloc, (void*)Point_dealloc},
                {0, NULL},
            };
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .legacy_slots = Point_slots,
                .defines = Point_defines,
            };
            @EXPORT_TYPE("Point", Point_spec)
            @INIT
        """
        with pytest.raises(TypeError) as err:
            mod = self.make_module(mod_src)
        assert "legacy tp_dealloc" in str(err.value)

    def test_metaclass_as_legacy_static_type(self):
        mod = self.make_module("""
            #include <Python.h>
            #include <structmember.h>

            @DEFINE_DummyMeta_struct

            /* This module is compiled as a shared library and some compilers
               don't allow addresses of Python objects defined in other
               libraries to be used in static initializers here. The
               DEFERRED_ADDRESS macro is just used for documentation and we
               need to set the actual value before we call PyType_Ready. */
            #define DEFERRED_ADDRESS(x) NULL

            static PyTypeObject DummyMetaType = {
                PyVarObject_HEAD_INIT(DEFERRED_ADDRESS(&PyType_Type), 0)
                .tp_name = "mytest.DummyMeta",
                .tp_basicsize = sizeof(DummyMeta),
                .tp_flags = Py_TPFLAGS_DEFAULT,
                .tp_base = DEFERRED_ADDRESS(&PyType_Type),
            };

            @DEFINE_Dummy_struct

            static PyMemberDef members[] = {
                    {"member", T_INT, offsetof(Dummy, member), 0, NULL},
                    {NULL, 0, 0, 0, NULL},
            };

            static PyType_Slot DummySlots[] = {
                {Py_tp_members, members},
                {0, NULL},
            };

            static HPyType_Spec Dummy_legacy_spec = {
                .name = "mytest.Dummy",
                .basicsize = sizeof(Dummy),
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
                .builtin_shape = HPyType_BuiltinShape_Legacy,
                .legacy_slots = DummySlots,
            };

            void setup_types(HPyContext *ctx, HPy module) {
                HPy h_DummyMeta;
                DummyMetaType.ob_base.ob_base.ob_type = &PyType_Type;
                DummyMetaType.tp_base = &PyType_Type;
                if (PyType_Ready(&DummyMetaType))
                    return;
                h_DummyMeta = HPy_FromPyObject(ctx, (PyObject*) &DummyMetaType);

                HPyType_SpecParam param[] = {
                    { HPyType_SpecParam_Metaclass, h_DummyMeta },
                    { (HPyType_SpecParam_Kind)0 }
                };
                HPy h_Dummy = HPyType_FromSpec(ctx, &Dummy_legacy_spec, param);
                if (!HPy_IsNull(h_Dummy)) {
                    HPy_SetAttr_s(ctx, module, "Dummy", h_Dummy);
                    HPy_SetAttr_s(ctx, module, "DummyMeta", h_DummyMeta);
                }

                HPy_Close(ctx, h_Dummy);
                HPy_Close(ctx, h_DummyMeta);
            }

            @DEFINE_meta_data_accessors

            @EXPORT(set_meta_data)
            @EXPORT(get_meta_data)
            @EXPORT(set_member)
            @EXTRA_INIT_FUNC(setup_types)
            @INIT
        """)

        assert isinstance(mod.Dummy, type)
        assert mod.DummyMeta is type(mod.Dummy)
        assert mod.set_meta_data(mod.Dummy) is None
        assert mod.get_meta_data(mod.Dummy) == 42 + 11
        # XXX TODO: Does DummyMeta_AsStruct() return anything?
        # XXX TODO: make sure Dummy_AsStruct and (Dummy*)pyobj point to the same memory

        d = mod.Dummy()
        mod.set_member(d)
        assert d.member == 123614

    def test_call_zero_basicsize_legacy(self):
        import pytest
        # type 'Dummy' has basicsize == 0; we cannot use the HPy call protocol
        # with legacy types that inherit their struct since we then don't know
        # how to safely allocate the hidden field
        with pytest.raises(TypeError):
            self.make_module("""
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

    def test_legacy_class(self):
        mod = self.make_module("""
            @DEFINE_PointObject
            @DEFINE_Point_xy
            static PyObject * point_class_getitem(PyObject *cls, PyObject *args)
            {
                Py_ssize_t args_len = PyTuple_Check(args) ? PyTuple_Size(args) : 1;
                if (args_len != 1) {
                    return PyErr_Format(PyExc_TypeError,
                                        "Too %s arguments for %s",
                                        args_len > 1 ? "many" : "few",
                                        ((PyTypeObject *)cls)->tp_name);
                }
                return Py_GenericAlias(cls, args);
            }

            static PyMethodDef point_methods[] = {
                /* for typing; requires python >= 3.9 */
                {"__class_getitem__",
                    (PyCFunction)point_class_getitem,
                    METH_CLASS | METH_O, NULL},
                {NULL, NULL, 0, NULL}           /* sentinel */
            };


            static PyType_Slot Point_slots[] = {
                {Py_tp_methods, point_methods},
                {Py_tp_new, (void*)PyType_GenericNew},
                {0, NULL},
            };
            static HPyDef *Point_defines[] = {&Point_x, &Point_y, NULL};
            static HPyType_Spec Point_spec = {
                .name = "mytest.Point",
                .basicsize = sizeof(PointObject),
                .builtin_shape = SHAPE(PointObject),
                .legacy_slots = Point_slots,
                .defines = Point_defines,
            };
            HPyDef_METH(basicsize, "basicsize", HPyFunc_O)
            static HPy basicsize_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                PyObject *o = HPy_AsPyObject(ctx, arg);
                size_t diff = ((PyTypeObject *)o)->tp_basicsize - sizeof(PointObject);
                HPy h_res = HPyLong_FromLong(ctx, diff);
                Py_DecRef(o);
                return h_res;
            }
            @EXPORT(basicsize)
            @EXPORT_TYPE("Point", Point_spec)
            @INIT
        """)
        # Calls __class_getitem__
        t = mod.Point[int]
        assert str(t) == "mytest.Point[int]"
        pt = mod.Point()
        assert pt.x == 0
        assert pt.y == 0
        assert mod.basicsize(mod.Point) == 0


class TestCustomLegacyFeatures(HPyTest):
    USE_CPYEXT = True

    def test_legacy_methods(self):
        mod = self.make_module("""
            #include <Python.h>

            static PyObject *f(PyObject *self, PyObject *args)
            {
                return PyLong_FromLong(1234);
            }
            static PyObject *g(PyObject *self, PyObject *arg)
            {
                long x = PyLong_AsLong(arg);
                return PyLong_FromLong(x * 2);
            }
            static PyObject *h(PyObject *self, PyObject *args)
            {
                long a, b, c;
                if (!PyArg_ParseTuple(args, "lll", &a, &b, &c))
                    return NULL;
                return PyLong_FromLong(100*a + 10*b + c);
            }
            static PyObject *k(PyObject *self, PyObject *args, PyObject *kwargs)
            {
                static const char *kwlist[] = { "a", "b", "c", NULL };
                long a, b, c;
                if (!PyArg_ParseTupleAndKeywords(args, kwargs, "lll", (char **)kwlist, &a, &b, &c))
                    return NULL;
                return PyLong_FromLong(100*a + 10*b + c);
            }

            static PyMethodDef my_legacy_methods[] = {
                {"f", (PyCFunction)f, METH_NOARGS},
                {"g", (PyCFunction)g, METH_O},
                {"h", (PyCFunction)h, METH_VARARGS},
                {"k", (PyCFunction)k, METH_VARARGS | METH_KEYWORDS},
                {NULL}
            };

            @EXPORT_LEGACY(my_legacy_methods)
            @INIT
        """)
        assert mod.f() == 1234
        assert mod.g(45) == 90
        assert mod.h(4, 5, 6) == 456
        assert mod.k(c=6, b=5, a=4) == 456

    def test_legacy_inherits_from_pure_raises(self):
        import pytest
        mod_src = """
            static HPyType_Spec PureType_spec = {
                .name = "mytest.PureType",
                .flags = HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE,
            };

            static HPyType_Spec LegacyType_spec = {
                .name = "mytest.LegacyType",
                .builtin_shape = HPyType_BuiltinShape_Legacy,
            };

            static void make_Types(HPyContext *ctx, HPy module)
            {
                HPy h_PureType = HPyType_FromSpec(ctx, &PureType_spec, NULL);
                if (HPy_IsNull(h_PureType)) {
                    return;
                }

                HPyType_SpecParam LegacyType_param[] = {
                    { HPyType_SpecParam_Base, h_PureType },
                    { (HPyType_SpecParam_Kind)0 }
                };
                HPy h_LegacyType = HPyType_FromSpec(
                    ctx, &LegacyType_spec, LegacyType_param);
                if (HPy_IsNull(h_LegacyType)) {
                    HPy_Close(ctx, h_PureType);
                    return;
                }
                HPy_Close(ctx, h_LegacyType);
                HPy_Close(ctx, h_PureType);
            }
            @EXTRA_INIT_FUNC(make_Types)
            @INIT
        """
        with pytest.raises(TypeError) as err:
            self.make_module(mod_src)
        assert str(err.value) == (
            "A legacy type should not inherit its memory layout from a"
            " pure type")


class TestInheritBaseLegacy(HPyTest):
    USE_CPYEXT = True

    def test_float64(self):
        # Recreate the numpy float64 scalar type
        mod = self.make_module("""
            #include <Python.h>
            #define HPY_BASEFLAGS HPy_TPFLAGS_DEFAULT | HPy_TPFLAGS_BASETYPE

            typedef struct {
                    PyObject_HEAD
                    double obval;
            } PyDoubleScalarObject;

            HPyGlobal float64global;

            HPyType_LEGACY_HELPERS(PyDoubleScalarObject);

            HPyDef_SLOT(double_arrtype_new, HPy_tp_new)
            static HPy
            double_arrtype_new_impl(HPyContext *ctx, HPy type, const HPy *args, HPy_ssize_t nargs, HPy kwds)
            {
                /* allow base-class (if any) to do conversion */
                HPy targs = HPyTuple_FromArray(ctx, (HPy*)args, nargs);

                HPy from_superclass = HPy_CallTupleDict(ctx, ctx->h_FloatType, targs, kwds);

                HPy_Close(ctx, targs);
                if (HPy_IsNull(from_superclass)) {
                    /* NumPy clears the error and does lots of other conversions
                       For this test, give up instead
                    */
                    return HPy_NULL;
                }
                else {
                    return from_superclass;
                }
            }

            static PyType_Slot PyGenericArrType_Type_slots_legacy[] = {
                {0},
            };

            static HPyDef *PyGenericArrType_Type_hpy_slots[] = {
                0
            };

            static PyType_Slot PyFloatingArrType_Type_slots_legacy[] = {
                {0},
            };

            static PyType_Slot PyDoubleArrType_Type_slots_legacy[] = {
                {0},
            };

            static HPyDef *PyDoubleArrType_Type_hpy_defines[] = {
                &double_arrtype_new,
                0
            };
           
            static HPyType_Spec PyGenericArrType_Type_spec = {
                .name = "numpy.generic",
                .flags = HPY_BASEFLAGS,
                .builtin_shape = HPyType_BuiltinShape_Legacy,
                .legacy_slots = &PyGenericArrType_Type_slots_legacy,
                .defines = PyGenericArrType_Type_hpy_slots,
                .basicsize = sizeof(PyObject),
            };

            HPyDef_METH(new_float64, "new_float64", HPyFunc_O)
            static HPy new_float64_impl(HPyContext *ctx, HPy self, HPy arg)
            {
                double a = HPyFloat_AsDouble(ctx, arg);
                HPy h_PyDoubleArrType_Type = HPyGlobal_Load(ctx, float64global);
                if (HPy_IsNull(h_PyDoubleArrType_Type))
                    return HPy_NULL;
                PyDoubleScalarObject  *val=NULL;
                HPy h_obj = HPy_New(ctx, h_PyDoubleArrType_Type, &val);
                HPy_Close(ctx, h_PyDoubleArrType_Type);
                /* XXX This value is not the one seen in the interpreter */
                val->obval = a;
                return h_obj;
            }


            void make_Float64(HPyContext *ctx, HPy module)
            {

                HPy h_PyGenericArrType_Type = 
                    HPyType_FromSpec(ctx, &PyGenericArrType_Type_spec, NULL);
                if (HPy_IsNull(h_PyGenericArrType_Type))
                    return;

                HPyType_SpecParam Floating_params[] = {
                    { HPyType_SpecParam_Base, h_PyGenericArrType_Type },
                    { 0 }, }; 

                HPyType_Spec PyFloatingArrType_Type_spec = {
                    .name = "numpy.floating",
                    .builtin_shape = HPyType_BuiltinShape_Legacy,
                    .legacy_slots = PyFloatingArrType_Type_slots_legacy,
                    .flags = HPY_BASEFLAGS,
                    .basicsize = sizeof(PyObject),
                };

                HPy h_PyFloatingArrType_Type = 
                    HPyType_FromSpec(ctx, &PyFloatingArrType_Type_spec, Floating_params);
                HPy_Close(ctx, h_PyGenericArrType_Type);
                if (HPy_IsNull(h_PyFloatingArrType_Type)) {
                    return;
                } 

                HPyType_Spec PyDoubleArrType_Type_spec = {
                    .name = "numpy.float64",
                    .basicsize = sizeof(PyDoubleScalarObject),
                    .builtin_shape = HPyType_BuiltinShape_Legacy,
                    .legacy_slots = PyDoubleArrType_Type_slots_legacy,
                    .flags = HPY_BASEFLAGS,
                    .defines = PyDoubleArrType_Type_hpy_defines,
                };

                HPyType_SpecParam Double_params[] = {
                    { HPyType_SpecParam_Base, h_PyFloatingArrType_Type },
                    { HPyType_SpecParam_Base, ctx->h_FloatType },
                    { (HPyType_SpecParam_Kind)0 }
                };

                HPy h_PyDoubleArrType_Type =
                   HPyType_FromSpec(ctx, &PyDoubleArrType_Type_spec, Double_params); 
                HPy_Close(ctx, h_PyFloatingArrType_Type);
                if (HPy_IsNull(h_PyDoubleArrType_Type))
                    return;
                HPy_SetAttr_s(ctx, module, "float64", h_PyDoubleArrType_Type);
                HPyGlobal_Store(ctx, &float64global, h_PyDoubleArrType_Type);
                HPy_Close(ctx, h_PyDoubleArrType_Type);
            };
            @EXTRA_INIT_FUNC(make_Float64)
            @EXPORT(new_float64)
            @EXPORT_GLOBAL(float64global)
            @INIT
        """)
        assert isinstance(mod.float64, type)
        assert mod.float64() == 0.0
        assert mod.float64(42) == 42.0
        assert mod.new_float64(0.0) == 0.0
        # Hmm, this doesn't work. The storage created in HPy_New is not the
        # one created in cpyext?
        assert mod.new_float64(42.0) == 42.0


