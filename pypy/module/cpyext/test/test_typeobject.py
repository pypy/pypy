from pypy.interpreter import gateway
from rpython.rtyper.lltypesystem import rffi
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.pyobject import make_ref, from_ref
from pypy.module.cpyext.typeobject import PyTypeObjectPtr

class AppTestTypeObject(AppTestCpythonExtensionBase):
    def test_typeobject(self):
        import sys
        module = self.import_module(name='foo')
        assert 'foo' in sys.modules
        assert "copy" in dir(module.fooType)
        obj = module.new()
        print(obj.foo)
        assert obj.foo == 42
        print("Obj has type", type(obj))
        assert type(obj) is module.fooType
        print("type of obj has type", type(type(obj)))
        print("type of type of obj has type", type(type(type(obj))))
        assert module.fooType.__doc__ == "foo is for testing."

    def test_typeobject_method_descriptor(self):
        module = self.import_module(name='foo')
        obj = module.new()
        obj2 = obj.copy()
        assert module.new().name == "Foo Example"
        c = module.fooType.copy
        assert not "im_func" in dir(module.fooType.copy)
        assert module.fooType.copy.__objclass__ is module.fooType
        assert "copy" in repr(module.fooType.copy)
        assert repr(module.fooType) == "<type 'foo.foo'>"
        assert repr(obj2) == "<Foo>"
        assert repr(module.fooType.__call__) == "<slot wrapper '__call__' of 'foo.foo' objects>"
        assert obj2(foo=1, bar=2) == dict(foo=1, bar=2)

        print(obj.foo)
        assert obj.foo == 42
        assert obj.int_member == obj.foo

    def test_typeobject_data_member(self):
        module = self.import_module(name='foo')
        obj = module.new()
        obj.int_member = 23
        assert obj.int_member == 23
        obj.int_member = 42
        raises(TypeError, "obj.int_member = 'not a number'")
        raises(TypeError, "del obj.int_member")
        raises(TypeError, "obj.int_member_readonly = 42")
        exc = raises(TypeError, "del obj.int_member_readonly")
        assert "readonly" in str(exc.value)
        raises(SystemError, "obj.broken_member")
        raises(SystemError, "obj.broken_member = 42")
        assert module.fooType.broken_member.__doc__ is None
        assert module.fooType.object_member.__doc__ == "A Python object."
        assert str(type(module.fooType.int_member)) == "<type 'member_descriptor'>"

    def test_typeobject_object_member(self):
        module = self.import_module(name='foo')
        obj = module.new()
        assert obj.object_member is None
        obj.object_member = "hello"
        assert obj.object_member == "hello"
        del obj.object_member
        del obj.object_member
        assert obj.object_member is None
        raises(AttributeError, "obj.object_member_ex")
        obj.object_member_ex = None
        assert obj.object_member_ex is None
        obj.object_member_ex = 42
        assert obj.object_member_ex == 42
        del obj.object_member_ex
        raises(AttributeError, "del obj.object_member_ex")

        obj.set_foo = 32
        assert obj.foo == 32

    def test_typeobject_string_member(self):
        module = self.import_module(name='foo')
        obj = module.new()
        assert obj.string_member == "Hello from PyPy"
        raises(TypeError, "obj.string_member = 42")
        raises(TypeError, "del obj.string_member")
        obj.unset_string_member()
        assert obj.string_member is None
        assert obj.string_member_inplace == "spam"
        raises(TypeError, "obj.string_member_inplace = 42")
        raises(TypeError, "del obj.string_member_inplace")
        assert obj.char_member == "s"
        obj.char_member = "a"
        assert obj.char_member == "a"
        raises(TypeError, "obj.char_member = 'spam'")
        raises(TypeError, "obj.char_member = 42")
        #
        import sys
        bignum = sys.maxint - 42
        obj.short_member = -12345;     assert obj.short_member == -12345
        obj.long_member = -bignum;     assert obj.long_member == -bignum
        obj.ushort_member = 45678;     assert obj.ushort_member == 45678
        obj.uint_member = 3000000000;  assert obj.uint_member == 3000000000
        obj.ulong_member = 2*bignum;   assert obj.ulong_member == 2*bignum
        obj.byte_member = -99;         assert obj.byte_member == -99
        obj.ubyte_member = 199;        assert obj.ubyte_member == 199
        obj.bool_member = True;        assert obj.bool_member is True
        obj.float_member = 9.25;       assert obj.float_member == 9.25
        obj.double_member = 9.25;      assert obj.double_member == 9.25
        obj.longlong_member = -2**59;  assert obj.longlong_member == -2**59
        obj.ulonglong_member = 2**63;  assert obj.ulonglong_member == 2**63
        obj.ssizet_member = sys.maxint;assert obj.ssizet_member == sys.maxint
        #

    def test_staticmethod(self):
        module = self.import_module(name="foo")
        obj = module.fooType.create()
        assert obj.foo == 42
        obj2 = obj.create()
        assert obj2.foo == 42

    def test_classmethod(self):
        module = self.import_module(name="foo")
        obj = module.fooType.classmeth()
        assert obj is module.fooType

    def test_new(self):
        # XXX cpython segfaults but if run singly (with -k test_new) this passes
        module = self.import_module(name='foo')
        obj = module.new()
        # call __new__
        newobj = module.UnicodeSubtype(u"xyz")
        assert newobj == u"xyz"
        assert isinstance(newobj, module.UnicodeSubtype)

        assert isinstance(module.fooType(), module.fooType)
        class bar(module.fooType):
            pass
        assert isinstance(bar(), bar)

        fuu = module.UnicodeSubtype
        class fuu2(fuu):
            def baz(self):
                return self
        assert fuu2(u"abc").baz().escape()
        raises(TypeError, module.fooType.object_member.__get__, 1)

    def test_multiple_inheritance1(self):
        module = self.import_module(name='foo')
        obj = module.UnicodeSubtype(u'xyz')
        obj2 = module.UnicodeSubtype2()
        obj3 = module.UnicodeSubtype3()
        assert obj3.get_val() == 42
        assert len(type(obj3).mro()) == 6

    def test_init(self):
        module = self.import_module(name="foo")
        newobj = module.UnicodeSubtype()
        assert newobj.get_val() == 42

        # this subtype should inherit tp_init
        newobj = module.UnicodeSubtype2()
        assert newobj.get_val() == 42

        # this subclass redefines __init__
        class UnicodeSubclass2(module.UnicodeSubtype):
            def __init__(self):
                self.foobar = 32
                super(UnicodeSubclass2, self).__init__()

        newobj = UnicodeSubclass2()
        assert newobj.get_val() == 42
        assert newobj.foobar == 32

    def test_metatype(self):
        module = self.import_module(name='foo')
        assert module.MetaType.__mro__ == (module.MetaType, type, object)
        x = module.MetaType('name', (), {})
        assert isinstance(x, type)
        assert isinstance(x, module.MetaType)
        x()

    def test_metaclass_compatible(self):
        # metaclasses should not conflict here
        module = self.import_module(name='foo')
        assert module.MetaType.__mro__ == (module.MetaType, type, object)
        assert type(module.fooType).__mro__ == (type, object)
        y = module.MetaType('other', (module.MetaType,), {})
        assert isinstance(y, module.MetaType)
        x = y('something', (type(y),), {})
        del x, y

    def test_metaclass_compatible2(self):
        skip('fails even with -A, fooType has BASETYPE flag')
        # XXX FIX - must raise since fooType (which is a base type)
        # does not have flag Py_TPFLAGS_BASETYPE
        module = self.import_module(name='foo')
        raises(TypeError, module.MetaType, 'other', (module.fooType,), {})

    def test_sre(self):
        import sys
        for m in ['_sre', 'sre_compile', 'sre_constants', 'sre_parse', 're']:
            # clear out these modules
            try:
                del sys.modules[m]
            except KeyError:
                pass
        module = self.import_module(name='_sre')
        import re
        assert re.sre_compile._sre is module
        s = u"Foo " * 1000 + u"Bar"
        prog = re.compile(ur"Foo.*Bar")
        assert prog.match(s)
        m = re.search(u"xyz", u"xyzxyz")
        assert m
        m = re.search("xyz", "xyzxyz")
        assert m
        assert "groupdict" in dir(m)
        re._cache.clear()
        re._cache_repl.clear()
        del prog, m

    def test_init_error(self):
        module = self.import_module("foo")
        raises(ValueError, module.InitErrType)

    def test_cmps(self):
        module = self.import_module("comparisons")
        cmpr = module.CmpType()
        assert cmpr == 3
        assert cmpr != 42

    def test_richcompare(self):
        module = self.import_module("comparisons")
        cmpr = module.CmpType()

        # should not crash
        cmpr < 4
        cmpr <= 4
        cmpr > 4
        cmpr >= 4

        assert cmpr.__le__(4) is NotImplemented

    def test_tpcompare(self):
        module = self.import_module("comparisons")
        cmpr = module.OldCmpType()
        assert cmpr < cmpr

    def test_hash(self):
        module = self.import_module("comparisons")
        cmpr = module.CmpType()
        assert hash(cmpr) == 3
        d = {}
        d[cmpr] = 72
        assert d[cmpr] == 72
        assert d[3] == 72

    def test_descriptor(self):
        module = self.import_module("foo")
        prop = module.Property()
        class C(object):
            x = prop
        obj = C()
        assert obj.x == (prop, obj, C)
        assert C.x == (prop, None, C)

        obj.x = 2
        assert obj.y == (prop, 2)
        del obj.x
        assert obj.z == prop

    def test_tp_dict(self):
        foo = self.import_module("foo")
        module = self.import_extension('test', [
           ("read_tp_dict", "METH_O",
            '''
                 PyObject *method;
                 if (!args->ob_type->tp_dict)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 method = PyDict_GetItemString(
                     args->ob_type->tp_dict, "copy");
                 Py_INCREF(method);
                 return method;
             '''),
            ("get_type_dict", "METH_O",
             '''
                PyObject* value = args->ob_type->tp_dict;
                if (value == NULL) value = Py_None;
                Py_INCREF(value);
                return value;
             '''),
            ])
        obj = foo.new()
        assert module.read_tp_dict(obj) == foo.fooType.copy
        d = module.get_type_dict(obj)
        assert type(d) is dict
        d["_some_attribute"] = 1
        assert type(obj)._some_attribute == 1
        del d["_some_attribute"]

        class A(object):
            pass
        obj = A()
        d = module.get_type_dict(obj)
        assert type(d) is dict
        d["_some_attribute"] = 1
        assert type(obj)._some_attribute == 1
        del d["_some_attribute"]

        d = module.get_type_dict(1)
        assert type(d) is dict
        try:
            d["_some_attribute"] = 1
        except TypeError:  # on PyPy, int.__dict__ is really immutable
            pass
        else:
            assert int._some_attribute == 1
            del d["_some_attribute"]

    def test_custom_allocation(self):
        foo = self.import_module("foo")
        obj = foo.newCustom()
        assert type(obj) is foo.Custom
        assert type(foo.Custom) is foo.MetaType

    def test_heaptype(self):
        module = self.import_extension('foo', [
           ("name_by_heaptype", "METH_O",
            '''
                 PyHeapTypeObject *heaptype = (PyHeapTypeObject *)args;
                 Py_INCREF(heaptype->ht_name);
                 return heaptype->ht_name;
             '''),
            ("setattr", "METH_O",
             '''
                int ret;
                PyObject* name = PyString_FromString("mymodule");
                PyObject *obj = PyType_Type.tp_alloc(&PyType_Type, 0);
                PyHeapTypeObject *type = (PyHeapTypeObject*)obj;
                if ((type->ht_type.tp_flags & Py_TPFLAGS_HEAPTYPE) == 0)
                {
                    PyErr_SetString(PyExc_ValueError,
                                    "Py_TPFLAGS_HEAPTYPE not set");
                    return NULL;
                }
                type->ht_type.tp_name = ((PyTypeObject*)args)->tp_name;
                PyType_Ready(&type->ht_type);
                ret = PyObject_SetAttrString((PyObject*)&type->ht_type,
                                    "__module__", name);
                Py_DECREF(name);
                if (ret < 0)
                    return NULL;
                return PyLong_FromLong(ret);
             '''),
            ])
        class C(object):
            pass
        assert module.name_by_heaptype(C) == "C"
        assert module.setattr(C) == 0


    def test_type_dict(self):
        foo = self.import_module("foo")
        module = self.import_extension('test', [
           ("hack_tp_dict", "METH_O",
            '''
                 PyTypeObject *type = args->ob_type;
                 PyObject *a1 = PyLong_FromLong(1);
                 PyObject *a2 = PyLong_FromLong(2);
                 PyObject *value;

                 if (PyDict_SetItemString(type->tp_dict, "a",
                         a1) < 0)
                     return NULL;
                 Py_DECREF(a1);
                 PyType_Modified(type);
                 value = PyObject_GetAttrString((PyObject*)type, "a");
                 Py_DECREF(value);

                 if (PyDict_SetItemString(type->tp_dict, "a",
                         a2) < 0)
                     return NULL;
                 Py_DECREF(a2);
                 PyType_Modified(type);
                 value = PyObject_GetAttrString((PyObject*)type, "a");
                 return value;
             '''
             )
            ])
        obj = foo.new()
        assert module.hack_tp_dict(obj) == 2


class TestTypes(BaseApiTest):
    def test_type_attributes(self, space, api):
        w_class = space.appexec([], """():
            class A(object):
                pass
            return A
            """)
        ref = make_ref(space, w_class)

        py_type = rffi.cast(PyTypeObjectPtr, ref)
        assert py_type.c_tp_alloc
        assert from_ref(space, py_type.c_tp_mro).wrappeditems is w_class.mro_w

        api.Py_DecRef(ref)

    def test_type_dict(self, space, api):
        w_class = space.appexec([], """():
            class A(object):
                pass
            return A
            """)
        ref = make_ref(space, w_class)

        py_type = rffi.cast(PyTypeObjectPtr, ref)
        w_dict = from_ref(space, py_type.c_tp_dict)
        w_name = space.wrap('a')
        space.setitem(w_dict, w_name, space.wrap(1))
        assert space.int_w(space.getattr(w_class, w_name)) == 1
        space.delitem(w_dict, w_name)

    def test_multiple_inheritance2(self, space, api):
        w_class = space.appexec([], """():
            class A(object):
                pass
            class B(object):
                pass
            class C(A, B):
                pass
            return C
            """)
        ref = make_ref(space, w_class)
        api.Py_DecRef(ref)

    def test_lookup(self, space, api):
        w_type = space.w_bytes
        w_obj = api._PyType_Lookup(w_type, space.wrap("upper"))
        assert space.is_w(w_obj, space.w_bytes.getdictvalue(space, "upper"))

        w_obj = api._PyType_Lookup(w_type, space.wrap("__invalid"))
        assert w_obj is None
        assert api.PyErr_Occurred() is None

    def test_ndarray_ref(self, space, api):
        w_obj = space.appexec([], """():
            import _numpypy
            return _numpypy.multiarray.dtype('int64').type(2)""")
        ref = make_ref(space, w_obj)
        api.Py_DecRef(ref)

class AppTestSlots(AppTestCpythonExtensionBase):
    def setup_class(cls):
        AppTestCpythonExtensionBase.setup_class.im_func(cls)
        def _check_type_object(w_X):
            assert w_X.is_cpytype()
            assert not w_X.is_heaptype()
        cls.w__check_type_object = cls.space.wrap(
            gateway.interp2app(_check_type_object))

    def test_some_slots(self):
        module = self.import_extension('foo', [
            ("test_type", "METH_O",
             '''
                 /* "args->ob_type" is a strange way to get at 'type',
                    which should have a different tp_getattro/tp_setattro
                    than its tp_base, which is 'object'.
                  */

                 if (!args->ob_type->tp_setattro)
                 {
                     PyErr_SetString(PyExc_ValueError, "missing tp_setattro");
                     return NULL;
                 }
                 if (args->ob_type->tp_setattro ==
                     args->ob_type->tp_base->tp_setattro)
                 {
                     /* Note that unlike CPython, in PyPy 'type.tp_setattro'
                        is the same function as 'object.tp_setattro'.  This
                        test used to check that it was not, but that was an
                        artifact of the bootstrap logic only---in the final
                        C sources I checked and they are indeed the same.
                        So we ignore this problem here. */
                 }
                 if (!args->ob_type->tp_getattro)
                 {
                     PyErr_SetString(PyExc_ValueError, "missing tp_getattro");
                     return NULL;
                 }
                 if (args->ob_type->tp_getattro ==
                     args->ob_type->tp_base->tp_getattro)
                 {
                     PyErr_SetString(PyExc_ValueError, "recursive tp_getattro");
                     return NULL;
                 }
                 Py_RETURN_TRUE;
             '''
             )
            ])
        assert module.test_type(type(None))

    def test_tp_getattro(self):
        module = self.import_extension('foo', [
            ("test_tp_getattro", "METH_VARARGS",
             '''
                 PyObject *name, *obj = PyTuple_GET_ITEM(args, 0);
                 PyIntObject *attr, *value = (PyIntObject*) PyTuple_GET_ITEM(args, 1);
                 if (!obj->ob_type->tp_getattro)
                 {
                     PyErr_SetString(PyExc_ValueError, "missing tp_getattro");
                     return NULL;
                 }
                 name = PyString_FromString("attr1");
                 attr = (PyIntObject*) obj->ob_type->tp_getattro(obj, name);
                 if (attr->ob_ival != value->ob_ival)
                 {
                     PyErr_SetString(PyExc_ValueError,
                                     "tp_getattro returned wrong value");
                     return NULL;
                 }
                 Py_DECREF(name);
                 Py_DECREF(attr);
                 name = PyString_FromString("attr2");
                 attr = (PyIntObject*) obj->ob_type->tp_getattro(obj, name);
                 if (attr == NULL && PyErr_ExceptionMatches(PyExc_AttributeError))
                 {
                     PyErr_Clear();
                 } else {
                     PyErr_SetString(PyExc_ValueError,
                                     "tp_getattro should have raised");
                     return NULL;
                 }
                 Py_DECREF(name);
                 Py_RETURN_TRUE;
             '''
             )
            ])
        class C:
            def __init__(self):
                self.attr1 = 123
        assert module.test_tp_getattro(C(), 123)

    def test_nb_int(self):
        module = self.import_extension('foo', [
            ("nb_int", "METH_VARARGS",
             '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 if (!type->tp_as_number ||
                     !type->tp_as_number->nb_int)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return type->tp_as_number->nb_int(obj);
             '''
             )
            ])
        assert module.nb_int(int, 10) == 10
        assert module.nb_int(float, -12.3) == -12
        raises(ValueError, module.nb_int, str, "123")
        class F(float):
            def __int__(self):
                return 666
        # as long as issue 2248 is not fixed, 'expected' is 666 on pypy,
        # but it should be -12.  This test is not concerned about that,
        # but only about getting the same answer with module.nb_int().
        expected = float.__int__(F(-12.3))
        assert module.nb_int(float, F(-12.3)) == expected

    def test_nb_float(self):
        module = self.import_extension('foo', [
            ("nb_float", "METH_VARARGS",
             '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 if (!type->tp_as_number ||
                     !type->tp_as_number->nb_float)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return type->tp_as_number->nb_float(obj);
             '''
             )
            ])
        assert module.nb_float(int, 10) == 10.0
        assert module.nb_float(float, -12.3) == -12.3
        raises(ValueError, module.nb_float, str, "123")
        #
        # check that calling PyInt_Type->tp_as_number->nb_float(x)
        # does not invoke a user-defined __float__()
        class I(int):
            def __float__(self):
                return -55.55
        class F(float):
            def __float__(self):
                return -66.66
        assert float(I(10)) == -55.55
        assert float(F(10.5)) == -66.66
        assert module.nb_float(int, I(10)) == 10.0
        assert module.nb_float(float, F(10.5)) == 10.5
        # XXX but the subtype's tp_as_number->nb_float(x) should really invoke
        # the user-defined __float__(); it doesn't so far
        #assert module.nb_float(I, I(10)) == -55.55
        #assert module.nb_float(F, F(10.5)) == -66.66

    def test_tp_call(self):
        module = self.import_extension('foo', [
            ("tp_call", "METH_VARARGS",
             '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 PyObject *c_args = PyTuple_GET_ITEM(args, 2);
                 if (!type->tp_call)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return type->tp_call(obj, c_args, NULL);
             '''
             )
            ])
        class C:
            def __call__(self, *args):
                return args
        assert module.tp_call(type(C()), C(), ('x', 2)) == ('x', 2)
        class D(type):
            def __call__(self, *args):
                return "foo! %r" % (args,)
        typ1 = D('d', (), {})
        #assert module.tp_call(D, typ1, ()) == "foo! ()" XXX not working so far
        assert isinstance(module.tp_call(type, typ1, ()), typ1)

    def test_tp_init(self):
        module = self.import_extension('foo', [
            ("tp_init", "METH_VARARGS",
             '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 PyObject *c_args = PyTuple_GET_ITEM(args, 2);
                 if (!type->tp_init)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 if (type->tp_init(obj, c_args, NULL) < 0)
                     return NULL;
                 Py_INCREF(Py_None);
                 return Py_None;
             '''
             )
            ])
        x = [42]
        assert module.tp_init(list, x, ("hi",)) is None
        assert x == ["h", "i"]
        class LL(list):
            def __init__(self, *ignored):
                raise Exception
        x = LL.__new__(LL)
        assert module.tp_init(list, x, ("hi",)) is None
        assert x == ["h", "i"]

    def test_tp_str(self):
        module = self.import_extension('foo', [
           ("tp_str", "METH_VARARGS",
            '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 if (!type->tp_str)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return type->tp_str(obj);
             '''
             )
            ])
        class C:
            def __str__(self):
                return "text"
        assert module.tp_str(type(C()), C()) == "text"
        class D(int):
            def __str__(self):
                return "more text"
        assert module.tp_str(int, D(42)) == "42"

    def test_mp_ass_subscript(self):
        module = self.import_extension('foo', [
           ("new_obj", "METH_NOARGS",
            '''
                PyObject *obj;
                obj = PyObject_New(PyObject, &Foo_Type);
                return obj;
            '''
            )], prologue='''
            static int
            mp_ass_subscript(PyObject *self, PyObject *key, PyObject *value)
            {
                if (PyInt_Check(key)) {
                    PyErr_SetNone(PyExc_ZeroDivisionError);
                    return -1;
                }
                return 0;
            }
            PyMappingMethods tp_as_mapping;
            static PyTypeObject Foo_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "foo.foo",
            };
            ''', more_init = '''
                Foo_Type.tp_flags = Py_TPFLAGS_DEFAULT;
                Foo_Type.tp_as_mapping = &tp_as_mapping;
                tp_as_mapping.mp_ass_subscript = mp_ass_subscript;
                if (PyType_Ready(&Foo_Type) < 0) INITERROR;
            ''')
        obj = module.new_obj()
        raises(ZeroDivisionError, obj.__setitem__, 5, None)
        res = obj.__setitem__('foo', None)
        assert res is None

    def test_sq_contains(self):
        module = self.import_extension('foo', [
           ("new_obj", "METH_NOARGS",
            '''
                PyObject *obj;
                obj = PyObject_New(PyObject, &Foo_Type);
                return obj;
            '''
            )], prologue='''
            static int
            sq_contains(PyObject *self, PyObject *value)
            {
                return 42;
            }
            PySequenceMethods tp_as_sequence;
            static PyTypeObject Foo_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "foo.foo",
            };
            ''', more_init='''
                Foo_Type.tp_flags = Py_TPFLAGS_DEFAULT;
                Foo_Type.tp_as_sequence = &tp_as_sequence;
                tp_as_sequence.sq_contains = sq_contains;
                if (PyType_Ready(&Foo_Type) < 0) INITERROR;
            ''')
        obj = module.new_obj()
        res = "foo" in obj
        assert res is True

    def test_tp_iter(self):
        module = self.import_extension('foo', [
           ("tp_iter", "METH_VARARGS",
            '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 if (!type->tp_iter)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 return type->tp_iter(obj);
             '''
             ),
           ("tp_iternext", "METH_VARARGS",
            '''
                 PyTypeObject *type = (PyTypeObject *)PyTuple_GET_ITEM(args, 0);
                 PyObject *obj = PyTuple_GET_ITEM(args, 1);
                 PyObject *result;
                 if (!type->tp_iternext)
                 {
                     PyErr_SetNone(PyExc_ValueError);
                     return NULL;
                 }
                 result = type->tp_iternext(obj);
                 if (!result && !PyErr_Occurred())
                     result = PyString_FromString("stop!");
                 return result;
             '''
             )
            ])
        l = [1]
        it = module.tp_iter(list, l)
        assert type(it) is type(iter([]))
        assert module.tp_iternext(type(it), it) == 1
        assert module.tp_iternext(type(it), it) == "stop!"
        #
        class LL(list):
            def __iter__(self):
                return iter(())
        ll = LL([1])
        it = module.tp_iter(list, ll)
        assert type(it) is type(iter([]))
        x = list(it)
        assert x == [1]

    def test_intlike(self):
        module = self.import_extension('foo', [
            ("newInt", "METH_VARARGS",
             """
                IntLikeObject *intObj;
                int intval;

                if (!PyArg_ParseTuple(args, "i", &intval))
                    return NULL;

                intObj = PyObject_New(IntLikeObject, &IntLike_Type);
                if (!intObj) {
                    return NULL;
                }

                intObj->value = intval;
                return (PyObject *)intObj;
             """),
            ("check", "METH_VARARGS", """
                IntLikeObject *intObj;
                int intval, isint;

                if (!PyArg_ParseTuple(args, "i", &intval))
                    return NULL;
                intObj = PyObject_New(IntLikeObject, &IntLike_Type);
                if (!intObj) {
                    return NULL;
                }
                intObj->value = intval;
                isint = PyNumber_Check((PyObject*)intObj);
                Py_DECREF((PyObject*)intObj);
                return PyInt_FromLong(isint);
            """),
            ], prologue= """
            typedef struct
            {
                PyObject_HEAD
                int value;
            } IntLikeObject;

            static int
            intlike_nb_nonzero(PyObject *o)
            {
                IntLikeObject *v = (IntLikeObject*)o;
                if (v->value == -42) {
                    PyErr_SetNone(PyExc_ValueError);
                    return -1;
                }
                /* Returning -1 should be for exceptions only! */
                return v->value;
            }

            static PyObject*
            intlike_nb_int(PyObject* o)
            {
                IntLikeObject *v = (IntLikeObject*)o;
                return PyInt_FromLong(v->value);
            }

            PyTypeObject IntLike_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                /*tp_name*/             "IntLike",
                /*tp_basicsize*/        sizeof(IntLikeObject),
            };
            static PyNumberMethods intlike_as_number;
            """, more_init="""
            IntLike_Type.tp_flags |= Py_TPFLAGS_DEFAULT;
            IntLike_Type.tp_as_number = &intlike_as_number;
            intlike_as_number.nb_nonzero = intlike_nb_nonzero;
            intlike_as_number.nb_int = intlike_nb_int;
            PyType_Ready(&IntLike_Type);
            """)
        assert not bool(module.newInt(0))
        assert bool(module.newInt(1))
        raises(SystemError, bool, module.newInt(-1))
        raises(ValueError, bool, module.newInt(-42))
        val = module.check(10);
        assert val == 1

    def test_mathfunc(self):
        module = self.import_extension('foo', [
            ("newInt", "METH_VARARGS",
             """
                IntLikeObject *intObj;
                long intval;

                if (!PyArg_ParseTuple(args, "l", &intval))
                    return NULL;

                intObj = PyObject_New(IntLikeObject, &IntLike_Type);
                if (!intObj) {
                    return NULL;
                }

                intObj->ival = intval;
                return (PyObject *)intObj;
             """),
             ("newIntNoOp", "METH_VARARGS",
             """
                IntLikeObjectNoOp *intObjNoOp;
                long intval;

                if (!PyArg_ParseTuple(args, "l", &intval))
                    return NULL;

                intObjNoOp = PyObject_New(IntLikeObjectNoOp, &IntLike_Type_NoOp);
                if (!intObjNoOp) {
                    return NULL;
                }

                intObjNoOp->ival = intval;
                return (PyObject *)intObjNoOp;
             """)], prologue="""
            #include <math.h>
            typedef struct
            {
                PyObject_HEAD
                long ival;
            } IntLikeObject;

            static PyObject *
            intlike_nb_add(PyObject *self, PyObject *other)
            {
                long val2, val1 = ((IntLikeObject *)(self))->ival;
                if (PyInt_Check(other)) {
                  long val2 = PyInt_AsLong(other);
                  return PyInt_FromLong(val1+val2);
                }

                val2 = ((IntLikeObject *)(other))->ival;
                return PyInt_FromLong(val1+val2);
            }

            static PyObject *
            intlike_nb_pow(PyObject *self, PyObject *other, PyObject * z)
            {
                long val2, val1 = ((IntLikeObject *)(self))->ival;
                if (PyInt_Check(other)) {
                  long val2 = PyInt_AsLong(other);
                  return PyInt_FromLong(val1+val2);
                }

                val2 = ((IntLikeObject *)(other))->ival;
                return PyInt_FromLong((int)pow(val1,val2));
             }

            PyTypeObject IntLike_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                /*tp_name*/             "IntLike",
                /*tp_basicsize*/        sizeof(IntLikeObject),
            };
            static PyNumberMethods intlike_as_number;

            typedef struct
            {
                PyObject_HEAD
                long ival;
            } IntLikeObjectNoOp;

            PyTypeObject IntLike_Type_NoOp = {
                PyVarObject_HEAD_INIT(NULL, 0)
                /*tp_name*/             "IntLikeNoOp",
                /*tp_basicsize*/        sizeof(IntLikeObjectNoOp),
            };
            """, more_init="""
                IntLike_Type.tp_as_number = &intlike_as_number;
                IntLike_Type.tp_flags |= Py_TPFLAGS_DEFAULT | Py_TPFLAGS_CHECKTYPES;
                intlike_as_number.nb_add = intlike_nb_add;
                intlike_as_number.nb_power = intlike_nb_pow;
                if (PyType_Ready(&IntLike_Type) < 0) INITERROR;
                IntLike_Type_NoOp.tp_flags |= Py_TPFLAGS_DEFAULT | Py_TPFLAGS_CHECKTYPES;
                if (PyType_Ready(&IntLike_Type_NoOp) < 0) INITERROR;
            """)
        a = module.newInt(1)
        b = module.newInt(2)
        c = 3
        d = module.newIntNoOp(4)
        assert (a + b) == 3
        assert (b + c) == 5
        assert (d + a) == 5
        assert pow(d,b) == 16

    def test_tp_new_in_subclass_of_type(self):
        module = self.import_module(name='foo3')
        module.footype("X", (object,), {})

    def test_app_subclass_of_c_type(self):
        import sys
        module = self.import_module(name='foo')
        size = module.size_of_instances(module.fooType)
        class f1(object):
            pass
        class f2(module.fooType):
            pass
        class bar(f1, f2):
            pass
        assert bar.__base__ is f2
        # On cpython, the size changes.
        if '__pypy__' in sys.builtin_module_names:
            assert module.size_of_instances(bar) == size
        else:
            assert module.size_of_instances(bar) >= size

    def test_app_cant_subclass_two_types(self):
        module = self.import_module(name='foo')
        try:
            class bar(module.fooType, module.UnicodeSubtype):
                pass
        except TypeError as e:
            import sys
            if '__pypy__' in sys.builtin_module_names:
                assert str(e) == 'instance layout conflicts in multiple inheritance'

            else:
                assert str(e) == ('Error when calling the metaclass bases\n'
                          '    multiple bases have instance lay-out conflict')
        else:
            raise AssertionError("did not get TypeError!")

    def test_call_tp_dealloc(self):
        module = self.import_extension('foo', [
            ("fetchFooType", "METH_VARARGS",
             """
                PyObject *o;
                o = PyObject_New(PyObject, &Foo_Type);
                init_foo(o);
                Py_DECREF(o);   /* calls dealloc_foo immediately */

                Py_INCREF(&Foo_Type);
                return (PyObject *)&Foo_Type;
             """),
            ("newInstance", "METH_O",
             """
                PyTypeObject *tp = (PyTypeObject *)args;
                PyObject *e = PyTuple_New(0);
                PyObject *o = tp->tp_new(tp, e, NULL);
                Py_DECREF(e);
                return o;
             """),
            ("getCounter", "METH_VARARGS",
             """
                return PyInt_FromLong(foo_counter);
             """)], prologue="""
            typedef struct {
                PyObject_HEAD
                int someval[99];
            } FooObject;
            static int foo_counter = 1000;
            static void dealloc_foo(PyObject *foo) {
                int i;
                foo_counter += 10;
                for (i = 0; i < 99; i++)
                    if (((FooObject *)foo)->someval[i] != 1000 + i)
                        foo_counter += 100000;   /* error! */
                Py_TYPE(foo)->tp_free(foo);
            }
            static void init_foo(PyObject *o)
            {
                int i;
                if (o->ob_type->tp_basicsize < sizeof(FooObject))
                    abort();
                for (i = 0; i < 99; i++)
                    ((FooObject *)o)->someval[i] = 1000 + i;
            }
            static PyObject *new_foo(PyTypeObject *t, PyObject *a, PyObject *k)
            {
                PyObject *o;
                foo_counter += 1000;
                o = t->tp_alloc(t, 0);
                init_foo(o);
                return o;
            }
            static PyTypeObject Foo_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "foo.foo",
            };
            """, more_init="""
                Foo_Type.tp_basicsize = sizeof(FooObject);
                Foo_Type.tp_dealloc = &dealloc_foo;
                Foo_Type.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_CHECKTYPES
                                    | Py_TPFLAGS_BASETYPE;
                Foo_Type.tp_new = &new_foo;
                Foo_Type.tp_free = &PyObject_Del;
                if (PyType_Ready(&Foo_Type) < 0) INITERROR;
            """)
        Foo = module.fetchFooType()
        assert module.getCounter() == 1010
        Foo(); Foo()
        for i in range(10):
            if module.getCounter() >= 3030:
                break
            # NB. use self.debug_collect() instead of gc.collect(),
            # otherwise rawrefcount's dealloc callback doesn't trigger
            self.debug_collect()
        assert module.getCounter() == 3030
        #
        class Bar(Foo):
            pass
        assert Foo.__new__ is Bar.__new__
        Bar(); Bar()
        for i in range(10):
            if module.getCounter() >= 5050:
                break
            self.debug_collect()
        assert module.getCounter() == 5050
        #
        module.newInstance(Foo)
        for i in range(10):
            if module.getCounter() >= 6060:
                break
            self.debug_collect()
        assert module.getCounter() == 6060
        #
        module.newInstance(Bar)
        for i in range(10):
            if module.getCounter() >= 7070:
                break
            self.debug_collect()
        assert module.getCounter() == 7070

    def test_tp_call_reverse(self):
        module = self.import_extension('foo', [
           ("new_obj", "METH_NOARGS",
            '''
                PyObject *obj;
                obj = PyObject_New(PyObject, &Foo_Type);
                return obj;
            '''
            )], prologue='''
            static PyObject *
            my_tp_call(PyObject *self, PyObject *args, PyObject *kwds)
            {
                return PyInt_FromLong(42);
            }
            static PyTypeObject Foo_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "foo.foo",
            };
            ''', more_init='''
                Foo_Type.tp_flags = Py_TPFLAGS_DEFAULT;
                Foo_Type.tp_call = &my_tp_call;
                if (PyType_Ready(&Foo_Type) < 0) INITERROR;
            ''')
        x = module.new_obj()
        assert x() == 42
        assert x(4, bar=5) == 42

    def test_custom_metaclass(self):
        module = self.import_extension('foo', [
           ("getMetaClass", "METH_NOARGS",
            '''
                Py_INCREF(&FooType_Type);
                return (PyObject *)&FooType_Type;
            '''
            )], prologue='''
            static PyTypeObject FooType_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "foo.Type",
            };
            ''', more_init='''
                FooType_Type.tp_flags = Py_TPFLAGS_DEFAULT;
                FooType_Type.tp_base = &PyType_Type;
                if (PyType_Ready(&FooType_Type) < 0) INITERROR;
            ''')
        FooType = module.getMetaClass()
        if not self.runappdirect:
            self._check_type_object(FooType)
        class X(object):
            __metaclass__ = FooType
        print repr(X)
        X()

    def test_multiple_inheritance3(self):
        module = self.import_extension('foo', [
           ("new_obj", "METH_NOARGS",
            '''
                PyObject *obj;
                PyTypeObject *Base1, *Base2, *Base12;
                Base1 =  (PyTypeObject*)PyType_Type.tp_alloc(&PyType_Type, 0);
                Base2 =  (PyTypeObject*)PyType_Type.tp_alloc(&PyType_Type, 0);
                Base12 =  (PyTypeObject*)PyType_Type.tp_alloc(&PyType_Type, 0);
                Base1->tp_name = "Base1";
                Base2->tp_name = "Base2";
                Base12->tp_name = "Base12";
                Base1->tp_basicsize = sizeof(PyHeapTypeObject);
                Base2->tp_basicsize = sizeof(PyHeapTypeObject);
                Base12->tp_basicsize = sizeof(PyHeapTypeObject);
                #ifndef PYPY_VERSION /* PyHeapTypeObject has no ht_qualname on PyPy */
                #if PY_MAJOR_VERSION >= 3 && PY_MINOR_VERSION >= 3
                {
                  PyObject * dummyname = PyBytes_FromString("dummy name");
                  ((PyHeapTypeObject*)Base1)->ht_qualname = dummyname;
                  ((PyHeapTypeObject*)Base2)->ht_qualname = dummyname;
                  ((PyHeapTypeObject*)Base12)->ht_qualname = dummyname;
                }
                #endif 
                #endif 
                Base1->tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HEAPTYPE;
                Base2->tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HEAPTYPE;
                Base12->tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HEAPTYPE;
                Base12->tp_base = Base1;
                Base12->tp_bases = PyTuple_Pack(2, Base1, Base2); 
                Base12->tp_doc = "The Base12 type or object";
                if (PyType_Ready(Base1) < 0) return NULL;
                if (PyType_Ready(Base2) < 0) return NULL;
                if (PyType_Ready(Base12) < 0) return NULL;
                obj = PyObject_New(PyObject, Base12);
                return obj;
            '''
            )])
        obj = module.new_obj()
        assert 'Base12' in str(obj)
        assert type(obj).__doc__ == "The Base12 type or object"
        assert obj.__doc__ == "The Base12 type or object"


