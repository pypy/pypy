from pypy.interpreter.function import Function
from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.module.cpyext.classobject import (
    PyClass_Check, PyClass_New, PyInstance_Check, PyInstance_New,
    PyInstance_NewRaw, _PyInstance_Lookup)
from pypy.module.cpyext.object import PyObject_GetAttr

class TestClassObject(BaseApiTest):
    def test_newinstance(self, space):
        w_class = space.appexec([], """():
            class C:
                x = None
                def __init__(self, *args, **kwargs):
                    self.x = 1
                    self.args = args
                    self.__dict__.update(kwargs)
            return C
        """)

        assert PyClass_Check(space, w_class)

        w_instance = PyInstance_NewRaw(space, w_class, None)
        assert PyInstance_Check(space, w_instance)
        assert space.getattr(w_instance, space.wrap('x')) is space.w_None

        w_instance = PyInstance_NewRaw(space, w_class, space.wrap(dict(a=3)))
        assert space.getattr(w_instance, space.wrap('x')) is space.w_None
        assert space.unwrap(space.getattr(w_instance, space.wrap('a'))) == 3

        w_instance = PyInstance_New(space, w_class,
                                        space.wrap((3,)), space.wrap(dict(y=2)))
        assert space.unwrap(space.getattr(w_instance, space.wrap('x'))) == 1
        assert space.unwrap(space.getattr(w_instance, space.wrap('y'))) == 2
        assert space.unwrap(space.getattr(w_instance, space.wrap('args'))) == (3,)

    def test_lookup(self, space):
        w_instance = space.appexec([], """():
            class C:
                def __init__(self):
                    self.x = None
                def f(self): pass
            return C()
        """)

        assert PyInstance_Check(space, w_instance)
        assert PyObject_GetAttr(space, w_instance, space.wrap('x')) is space.w_None
        assert _PyInstance_Lookup(space, w_instance, space.wrap('x')) is space.w_None
        assert _PyInstance_Lookup(space, w_instance, space.wrap('y')) is None

        # getattr returns a bound method
        assert not isinstance(
            PyObject_GetAttr(space, w_instance, space.wrap('f')), Function)
        # _PyInstance_Lookup returns the raw descriptor
        assert isinstance(
            _PyInstance_Lookup(space, w_instance, space.wrap('f')), Function)

    def test_pyclass_new(self, space):
        w_bases = space.newtuple([])
        w_dict = space.newdict()
        w_name = space.wrap("C")
        w_class = PyClass_New(space, w_bases, w_dict, w_name)
        assert not space.isinstance_w(w_class, space.w_type)
        w_instance = space.call_function(w_class)
        assert PyInstance_Check(space, w_instance)
        assert space.is_true(space.call_method(space.builtin, "isinstance",
                                               w_instance, w_class))

class AppTestStringObject(AppTestCpythonExtensionBase):
    def test_class_type(self):
        module = self.import_extension('foo', [
            ("get_classtype", "METH_NOARGS",
             """
                 Py_INCREF(&PyClass_Type);
                 return (PyObject*)&PyClass_Type;
             """)])
        class C:
            pass
        assert module.get_classtype() is type(C)

    def test_pyclass_new_no_bases(self):
        module = self.import_extension('foo', [
            ("new_foo", "METH_O",
             """
                 return PyClass_New(NULL, PyDict_New(), args);
             """)])
        FooClass = module.new_foo("FooClass")
        class Cls1:
            pass
        assert type(FooClass) is type(Cls1)
        assert FooClass.__bases__ == Cls1.__bases__
