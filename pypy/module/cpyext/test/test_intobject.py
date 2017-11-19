from pypy.module.cpyext.test.test_api import BaseApiTest, raises_w
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.intobject import (
    PyInt_Check, PyInt_AsLong, PyInt_AS_LONG, PyInt_FromLong,
    PyInt_AsUnsignedLong, PyInt_AsUnsignedLongMask,
    PyInt_AsUnsignedLongLongMask)
import sys

class TestIntObject(BaseApiTest):
    def test_intobject(self, space):
        assert PyInt_Check(space, space.wrap(3))
        assert PyInt_Check(space, space.w_True)
        assert not PyInt_Check(space, space.wrap((1, 2, 3)))
        for i in [3, -5, -1, -sys.maxint, sys.maxint - 1]:
            x = PyInt_AsLong(space, space.wrap(i))
            y = PyInt_AS_LONG(space, space.wrap(i))
            assert x == i
            assert y == i
            w_x = PyInt_FromLong(space, x + 1)
            assert space.type(w_x) is space.w_int
            assert space.eq_w(w_x, space.wrap(i + 1))

        with raises_w(space, TypeError):
            PyInt_AsLong(space, space.w_None)

        with raises_w(space, TypeError):
            PyInt_AsLong(space, None)

        assert PyInt_AsUnsignedLong(space, space.wrap(sys.maxint)) == sys.maxint
        with raises_w(space, ValueError):
            PyInt_AsUnsignedLong(space, space.wrap(-5))

        assert (PyInt_AsUnsignedLongMask(space, space.wrap(sys.maxint))
                == sys.maxint)
        assert (PyInt_AsUnsignedLongMask(space, space.wrap(10 ** 30))
                == 10 ** 30 % ((sys.maxint + 1) * 2))

        assert (PyInt_AsUnsignedLongLongMask(space, space.wrap(sys.maxint))
                == sys.maxint)
        assert (PyInt_AsUnsignedLongLongMask(space, space.wrap(10 ** 30))
                == 10 ** 30 % (2 ** 64))

    def test_coerce(self, space):
        w_obj = space.appexec([], """():
            class Coerce(object):
                def __int__(self):
                    return 42
            return Coerce()""")
        assert PyInt_AsLong(space, w_obj) == 42

class AppTestIntObject(AppTestCpythonExtensionBase):
    def test_fromstring(self):
        module = self.import_extension('foo', [
            ("from_string", "METH_NOARGS",
             """
                 return PyInt_FromString("1234", NULL, 16);
             """),
            ])
        assert module.from_string() == 0x1234
        assert type(module.from_string()) is int

    def test_size_t(self):
        module = self.import_extension('foo', [
            ("values", "METH_NOARGS",
             """
                 return Py_BuildValue("NNNN",
                     PyInt_FromSize_t(123),
                     PyInt_FromSize_t((size_t)-1),
                     PyInt_FromSsize_t(123),
                     PyInt_FromSsize_t((size_t)-1));
             """),
            ])
        values = module.values()
        types = [type(x) for x in values]
        assert types == [int, long, int, int]

    def test_int_subtype(self):
        module = self.import_extension(
            'foo', [
            ("newEnum", "METH_VARARGS",
             """
                EnumObject *enumObj;
                int intval;
                PyObject *name;

                if (!PyArg_ParseTuple(args, "Oi", &name, &intval))
                    return NULL;

                enumObj = PyObject_New(EnumObject, &Enum_Type);
                if (!enumObj) {
                    return NULL;
                }

                enumObj->ob_ival = intval;
                Py_INCREF(name);
                enumObj->ob_name = name;

                return (PyObject *)enumObj;
             """),
            ],
            prologue="""
            #include "structmember.h"
            typedef struct
            {
                PyObject_HEAD
                long ob_ival;
                PyObject* ob_name;
            } EnumObject;

            static void
            enum_dealloc(PyObject *op)
            {
                    Py_DECREF(((EnumObject *)op)->ob_name);
                    Py_TYPE(op)->tp_free(op);
            }

            static PyMemberDef enum_members[] = {
                {"name", T_OBJECT, offsetof(EnumObject, ob_name), 0, NULL},
                {NULL}  /* Sentinel */
            };

            PyTypeObject Enum_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                /*tp_name*/             "Enum",
                /*tp_basicsize*/        sizeof(EnumObject),
                /*tp_itemsize*/         0,
                /*tp_dealloc*/          enum_dealloc,
                /*tp_print*/            0,
                /*tp_getattr*/          0,
                /*tp_setattr*/          0,
                /*tp_compare*/          0,
                /*tp_repr*/             0,
                /*tp_as_number*/        0,
                /*tp_as_sequence*/      0,
                /*tp_as_mapping*/       0,
                /*tp_hash*/             0,
                /*tp_call*/             0,
                /*tp_str*/              0,
                /*tp_getattro*/         0,
                /*tp_setattro*/         0,
                /*tp_as_buffer*/        0,
                /*tp_flags*/            Py_TPFLAGS_DEFAULT|Py_TPFLAGS_BASETYPE,
                /*tp_doc*/              0,
                /*tp_traverse*/         0,
                /*tp_clear*/            0,
                /*tp_richcompare*/      0,
                /*tp_weaklistoffset*/   0,
                /*tp_iter*/             0,
                /*tp_iternext*/         0,
                /*tp_methods*/          0,
                /*tp_members*/          enum_members,
                /*tp_getset*/           0,
                /*tp_base*/             0, /* set to &PyInt_Type in init function for MSVC */
                /*tp_dict*/             0,
                /*tp_descr_get*/        0,
                /*tp_descr_set*/        0,
                /*tp_dictoffset*/       0,
                /*tp_init*/             0,
                /*tp_alloc*/            0,
                /*tp_new*/              0
            };
            """, more_init = '''
                Enum_Type.tp_base = &PyInt_Type;
                if (PyType_Ready(&Enum_Type) < 0) INITERROR;
            ''')

        a = module.newEnum("ULTIMATE_ANSWER", 42)
        assert type(a).__name__ == "Enum"
        assert isinstance(a, int)
        assert a == int(a) == 42
        assert a.name == "ULTIMATE_ANSWER"

    def test_int_cast(self):
        mod = self.import_extension('foo', [
                #prove it works for ints
                ("test_int", "METH_NOARGS",
                """
                PyObject * obj = PyInt_FromLong(42);
                PyObject * val;
                if (!PyInt_Check(obj)) {
                    Py_DECREF(obj);
                    PyErr_SetNone(PyExc_ValueError);
                    return NULL;
                }
                val = PyInt_FromLong(((PyIntObject *)obj)->ob_ival);
                Py_DECREF(obj);
                return val;
                """
                ),
                ])
        i = mod.test_int()
        assert isinstance(i, int)
        assert i == 42

    def test_int_macros(self):
        mod = self.import_extension('foo', [
                ("test_macros", "METH_NOARGS",
                """
                PyObject * obj = PyInt_FromLong(42);
                PyIntObject * i = (PyIntObject*)obj;
                PyInt_AS_LONG(obj);
                PyInt_AS_LONG(i);
                Py_RETURN_NONE;
                """
                ),
                ])
