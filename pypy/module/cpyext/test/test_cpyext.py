import sys
import weakref
import os.path

import py

from pypy.conftest import gettestobjspace
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app
from pypy.rpython.lltypesystem import rffi, lltype, ll2ctypes
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator import platform
from pypy.translator.gensupp import uniquemodulename
from pypy.tool.udir import udir
from pypy.module.cpyext import api
from pypy.module.cpyext.state import State
from pypy.module.cpyext.pyobject import RefcountState
from pypy.module.cpyext.pyobject import Py_DecRef, InvalidPointerException
from pypy.translator.goal import autopath
from pypy.tool.identity_dict import identity_dict
from pypy.tool import leakfinder

@api.cpython_api([], api.PyObject)
def PyPy_Crash1(space):
    1/0

@api.cpython_api([], lltype.Signed, error=-1)
def PyPy_Crash2(space):
    1/0

class TestApi:
    def test_signature(self):
        assert 'PyModule_Check' in api.FUNCTIONS
        assert api.FUNCTIONS['PyModule_Check'].argtypes == [api.PyObject]

class AppTestApi:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['cpyext', 'thread', '_rawffi'])
        from pypy.rlib.libffi import get_libc_name
        cls.w_libc = cls.space.wrap(get_libc_name())

    def test_load_error(self):
        import cpyext
        raises(ImportError, cpyext.load_module, "missing.file", "foo")
        raises(ImportError, cpyext.load_module, self.libc, "invalid.function")

    def test_dllhandle(self):
        import sys
        if sys.platform != "win32" or sys.version_info < (2, 6):
            skip("Windows Python >= 2.6 only")
        assert sys.dllhandle
        assert sys.dllhandle.getaddressindll('PyPyErr_NewException')
        import ctypes # slow
        PyUnicode_GetDefaultEncoding = ctypes.pythonapi.PyPyUnicode_GetDefaultEncoding
        PyUnicode_GetDefaultEncoding.restype = ctypes.c_char_p
        assert PyUnicode_GetDefaultEncoding() == 'ascii'

def compile_module(space, modname, **kwds):
    """
    Build an extension module and return the filename of the resulting native
    code file.

    modname is the name of the module, possibly including dots if it is a module
    inside a package.

    Any extra keyword arguments are passed on to ExternalCompilationInfo to
    build the module (so specify your source with one of those).
    """
    modname = modname.split('.')[-1]
    eci = ExternalCompilationInfo(
        export_symbols=['init%s' % (modname,)],
        include_dirs=api.include_dirs,
        **kwds
        )
    eci = eci.convert_sources_to_files()
    dirname = (udir/uniquemodulename('module')).ensure(dir=1)
    soname = platform.platform.compile(
        [], eci,
        outputfilename=str(dirname/modname),
        standalone=False)
    from pypy.module.imp.importing import get_so_extension
    pydname = soname.new(purebasename=modname, ext=get_so_extension(space))
    soname.rename(pydname)
    return str(pydname)

def freeze_refcnts(self):
    state = self.space.fromcache(RefcountState)
    self.frozen_refcounts = {}
    for w_obj, obj in state.py_objects_w2r.iteritems():
        self.frozen_refcounts[w_obj] = obj.c_ob_refcnt
    #state.print_refcounts()
    self.frozen_ll2callocations = set(ll2ctypes.ALLOCATED.values())

class LeakCheckingTest(object):
    enable_leak_checking = True

    @staticmethod
    def cleanup_references(space):
        state = space.fromcache(RefcountState)

        import gc; gc.collect()
        # Clear all lifelines, objects won't resurrect
        for w_obj, obj in state.lifeline_dict._dict.items():
            if w_obj not in state.py_objects_w2r:
                state.lifeline_dict.set(w_obj, None)
            del obj
        import gc; gc.collect()

        try:
            del space.getexecutioncontext().cpyext_threadstate
        except AttributeError:
            pass

        for w_obj in state.non_heaptypes_w:
            Py_DecRef(space, w_obj)
        state.non_heaptypes_w[:] = []
        state.reset_borrowed_references()

    def check_and_print_leaks(self):
        # check for sane refcnts
        import gc

        if not self.enable_leak_checking:
            leakfinder.stop_tracking_allocations(check=False)
            return False

        leaking = False
        state = self.space.fromcache(RefcountState)
        gc.collect()
        lost_objects_w = identity_dict()
        lost_objects_w.update((key, None) for key in self.frozen_refcounts.keys())

        for w_obj, obj in state.py_objects_w2r.iteritems():
            base_refcnt = self.frozen_refcounts.get(w_obj)
            delta = obj.c_ob_refcnt
            if base_refcnt is not None:
                delta -= base_refcnt
                lost_objects_w.pop(w_obj)
            if delta != 0:
                leaking = True
                print >>sys.stderr, "Leaking %r: %i references" % (w_obj, delta)
                try:
                    weakref.ref(w_obj)
                except TypeError:
                    lifeline = None
                else:
                    lifeline = state.lifeline_dict.get(w_obj)
                if lifeline is not None:
                    refcnt = lifeline.pyo.c_ob_refcnt
                    if refcnt > 0:
                        print >>sys.stderr, "\tThe object also held by C code."
                    else:
                        referrers_repr = []
                        for o in gc.get_referrers(w_obj):
                            try:
                                repr_str = repr(o)
                            except TypeError, e:
                                repr_str = "%s (type of o is %s)" % (str(e), type(o))
                            referrers_repr.append(repr_str)
                        referrers = ", ".join(referrers_repr)
                        print >>sys.stderr, "\tThe object is referenced by these objects:", \
                                referrers
        for w_obj in lost_objects_w:
            print >>sys.stderr, "Lost object %r" % (w_obj, )
            leaking = True
        # the actual low-level leak checking is done by pypy.tool.leakfinder,
        # enabled automatically by pypy.conftest.
        return leaking

class AppTestCpythonExtensionBase(LeakCheckingTest):
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['cpyext', 'thread', '_rawffi'])
        cls.space.getbuiltinmodule("cpyext")
        from pypy.module.imp.importing import importhook
        importhook(cls.space, "os") # warm up reference counts
        state = cls.space.fromcache(RefcountState)
        state.non_heaptypes_w[:] = []

    def compile_module(self, name, **kwds):
        """
        Build an extension module linked against the cpyext api library.
        """
        state = self.space.fromcache(State)
        api_library = state.api_lib
        if sys.platform == 'win32':
            kwds["libraries"] = [api_library]
            # '%s' undefined; assuming extern returning int
            kwds["compile_extra"] = ["/we4013"]
        else:
            kwds["link_files"] = [str(api_library + '.so')]
            if sys.platform.startswith('linux'):
                kwds["compile_extra"]=["-Werror=implicit-function-declaration"]
        return compile_module(self.space, name, **kwds)


    def import_module(self, name, init=None, body='', load_it=True, filename=None):
        """
        init specifies the overall template of the module.

        if init is None, the module source will be loaded from a file in this
        test direcory, give a name given by the filename parameter.

        if filename is None, the module name will be used to construct the
        filename.
        """
        if init is not None:
            code = """
            #include <Python.h>
            %(body)s

            void init%(name)s(void) {
            %(init)s
            }
            """ % dict(name=name, init=init, body=body)
            kwds = dict(separate_module_sources=[code])
        else:
            if filename is None:
                filename = name
            filename = py.path.local(autopath.pypydir) / 'module' \
                    / 'cpyext'/ 'test' / (filename + ".c")
            kwds = dict(separate_module_files=[filename])

        mod = self.compile_module(name, **kwds)

        if load_it:
            api.load_extension_module(self.space, mod, name)
            self.imported_module_names.append(name)
            return self.space.getitem(
                self.space.sys.get('modules'),
                self.space.wrap(name))
        else:
            return os.path.dirname(mod)

    def reimport_module(self, mod, name):
        api.load_extension_module(self.space, mod, name)
        return self.space.getitem(
            self.space.sys.get('modules'),
            self.space.wrap(name))

    def import_extension(self, modname, functions, prologue=""):
        methods_table = []
        codes = []
        for funcname, flags, code in functions:
            cfuncname = "%s_%s" % (modname, funcname)
            methods_table.append("{\"%s\", %s, %s}," %
                                 (funcname, cfuncname, flags))
            func_code = """
            static PyObject* %s(PyObject* self, PyObject* args)
            {
            %s
            }
            """ % (cfuncname, code)
            codes.append(func_code)

        body = prologue + "\n".join(codes) + """
        static PyMethodDef methods[] = {
        %s
        { NULL }
        };
        """ % ('\n'.join(methods_table),)
        init = """Py_InitModule("%s", methods);""" % (modname,)
        return self.import_module(name=modname, init=init, body=body)

    def record_imported_module(self, name):
        """
        Record a module imported in a test so that it can be cleaned up in
        teardown before the check for leaks is done.

        name gives the name of the module in the space's sys.modules.
        """
        self.imported_module_names.append(name)

    def setup_method(self, func):
        # A list of modules which the test caused to be imported (in
        # self.space).  These will be cleaned up automatically in teardown.
        self.imported_module_names = []

        self.w_import_module = self.space.wrap(self.import_module)
        self.w_reimport_module = self.space.wrap(self.reimport_module)
        self.w_import_extension = self.space.wrap(self.import_extension)
        self.w_compile_module = self.space.wrap(self.compile_module)
        self.w_record_imported_module = self.space.wrap(
            self.record_imported_module)
        self.w_here = self.space.wrap(
            str(py.path.local(autopath.pypydir)) + '/module/cpyext/test/')


        # create the file lock before we count allocations
        self.space.call_method(self.space.sys.get("stdout"), "flush")

        freeze_refcnts(self)
        #self.check_and_print_leaks()

    def unimport_module(self, name):
        """
        Remove the named module from the space's sys.modules.
        """
        w_modules = self.space.sys.get('modules')
        w_name = self.space.wrap(name)
        self.space.delitem(w_modules, w_name)

    def teardown_method(self, func):
        for name in self.imported_module_names:
            self.unimport_module(name)
        self.cleanup_references(self.space)
        if self.check_and_print_leaks():
            assert False, (
                "Test leaks or loses object(s).  You should also check if "
                "the test actually passed in the first place; if it failed "
                "it is likely to reach this place.")
            # XXX find out how to disable check_and_print_leaks() if the
            # XXX test failed...


class AppTestCpythonExtension(AppTestCpythonExtensionBase):
    def test_createmodule(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", NULL);
        """
        self.import_module(name='foo', init=init)
        assert 'foo' in sys.modules

    def test_export_function(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyObject* foo_pi(PyObject* self, PyObject *args)
        {
            return PyFloat_FromDouble(3.14);
        }
        static PyMethodDef methods[] = {
            { "return_pi", foo_pi, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert 'foo' in sys.modules
        assert 'return_pi' in dir(module)
        assert module.return_pi is not None
        assert module.return_pi() == 3.14
        assert module.return_pi.__module__ == 'foo'


    def test_export_docstring(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyDoc_STRVAR(foo_pi_doc, "Return pi.");
        PyObject* foo_pi(PyObject* self, PyObject *args)
        {
            return PyFloat_FromDouble(3.14);
        }
        static PyMethodDef methods[] ={
            { "return_pi", foo_pi, METH_NOARGS, foo_pi_doc },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        doc = module.return_pi.__doc__
        assert doc == "Return pi."


    def test_InitModule4(self):
        init = """
        PyObject *cookie = PyFloat_FromDouble(3.14);
        Py_InitModule4("foo", methods, "docstring",
                       cookie, PYTHON_API_VERSION);
        Py_DECREF(cookie);
        """
        body = """
        PyObject* return_cookie(PyObject* self, PyObject *args)
        {
            if (self)
            {
                Py_INCREF(self);
                return self;
            }
            else
                Py_RETURN_FALSE;
        }
        static PyMethodDef methods[] = {
            { "return_cookie", return_cookie, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert module.__doc__ == "docstring"
        assert module.return_cookie() == 3.14

    def test_load_dynamic(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", NULL);
        """
        foo = self.import_module(name='foo', init=init)
        assert 'foo' in sys.modules
        del sys.modules['foo']
        import imp
        foo2 = imp.load_dynamic('foo', foo.__file__)
        assert 'foo' in sys.modules
        assert foo.__dict__ == foo2.__dict__

    def test_InitModule4_dotted(self):
        """
        If the module name passed to Py_InitModule4 includes a package, only
        the module name (the part after the last dot) is considered when
        computing the name of the module initializer function.
        """
        expected_name = "pypy.module.cpyext.test.dotted"
        module = self.import_module(name=expected_name, filename="dotted")
        assert module.__name__ == expected_name


    def test_InitModule4_in_package(self):
        """
        If `apple.banana` is an extension module which calls Py_InitModule4 with
        only "banana" as a name, the resulting module nevertheless is stored at
        `sys.modules["apple.banana"]`.
        """
        module = self.import_module(name="apple.banana", filename="banana")
        assert module.__name__ == "apple.banana"


    def test_recursive_package_import(self):
        """
        If `cherry.date` is an extension module which imports `apple.banana`,
        the latter is added to `sys.modules` for the `"apple.banana"` key.
        """
        # Build the extensions.
        banana = self.compile_module(
            "apple.banana", separate_module_files=[self.here + 'banana.c'])
        self.record_imported_module("apple.banana")
        date = self.compile_module(
            "cherry.date", separate_module_files=[self.here + 'date.c'])
        self.record_imported_module("cherry.date")

        # Set up some package state so that the extensions can actually be
        # imported.
        import sys, types, os
        cherry = sys.modules['cherry'] = types.ModuleType('cherry')
        cherry.__path__ = [os.path.dirname(date)]

        apple = sys.modules['apple'] = types.ModuleType('apple')
        apple.__path__ = [os.path.dirname(banana)]

        import cherry.date
        import apple.banana

        assert sys.modules['apple.banana'].__name__ == 'apple.banana'
        assert sys.modules['cherry.date'].__name__ == 'cherry.date'


    def test_modinit_func(self):
        """
        A module can use the PyMODINIT_FUNC macro to declare or define its
        module initializer function.
        """
        module = self.import_module(name='modinit')
        assert module.__name__ == 'modinit'


    def test_export_function2(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        static PyObject* my_objects[1];
        static PyObject* foo_cached_pi(PyObject* self, PyObject *args)
        {
            if (my_objects[0] == NULL) {
                my_objects[0] = PyFloat_FromDouble(3.14);
            }
            Py_INCREF(my_objects[0]);
            return my_objects[0];
        }
        static PyObject* foo_drop_pi(PyObject* self, PyObject *args)
        {
            if (my_objects[0] != NULL) {
                Py_DECREF(my_objects[0]);
                my_objects[0] = NULL;
            }
            Py_INCREF(Py_None);
            return Py_None;
        }
        static PyObject* foo_retinvalid(PyObject* self, PyObject *args)
        {
            return (PyObject*)0xAFFEBABE;
        }
        static PyMethodDef methods[] = {
            { "return_pi", foo_cached_pi, METH_NOARGS },
            { "drop_pi",   foo_drop_pi, METH_NOARGS },
            { "return_invalid_pointer", foo_retinvalid, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert module.return_pi() == 3.14
        print "A"
        module.drop_pi()
        print "B"
        module.drop_pi()
        print "C"
        assert module.return_pi() == 3.14
        print "D"
        assert module.return_pi() == 3.14
        print "E"
        module.drop_pi()
        skip("Hmm, how to check for the exception?")
        raises(api.InvalidPointerException, module.return_invalid_pointer)

    def test_argument(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyObject* foo_test(PyObject* self, PyObject *args)
        {
            PyObject *t = PyTuple_GetItem(args, 0);
            Py_INCREF(t);
            return t;
        }
        static PyMethodDef methods[] = {
            { "test", foo_test, METH_VARARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert module.test(True, True) == True

    def test_exception(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        static PyObject* foo_pi(PyObject* self, PyObject *args)
        {
            PyErr_SetString(PyExc_Exception, "moo!");
            return NULL;
        }
        static PyMethodDef methods[] = {
            { "raise_exception", foo_pi, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        exc = raises(Exception, module.raise_exception)
        if type(exc.value) is not Exception:
            raise exc.value

        assert exc.value.message == "moo!"

    def test_refcount(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        static PyObject* foo_pi(PyObject* self, PyObject *args)
        {
            PyObject *true = Py_True;
            int refcnt = true->ob_refcnt;
            int refcnt_after;
            Py_INCREF(true);
            Py_INCREF(true);
            PyBool_Check(true);
            refcnt_after = true->ob_refcnt;
            Py_DECREF(true);
            Py_DECREF(true);
            fprintf(stderr, "REFCNT %i %i\\n", refcnt, refcnt_after);
            return PyBool_FromLong(refcnt_after == refcnt+2 && refcnt < 3);
        }
        static PyObject* foo_bar(PyObject* self, PyObject *args)
        {
            PyObject *true = Py_True;
            PyObject *tup = NULL;
            int refcnt = true->ob_refcnt;
            int refcnt_after;

            tup = PyTuple_New(1);
            Py_INCREF(true);
            if (PyTuple_SetItem(tup, 0, true) < 0)
                return NULL;
            refcnt_after = true->ob_refcnt;
            Py_DECREF(tup);
            fprintf(stderr, "REFCNT2 %i %i\\n", refcnt, refcnt_after);
            return PyBool_FromLong(refcnt_after == refcnt);
        }

        static PyMethodDef methods[] = {
            { "test_refcount", foo_pi, METH_NOARGS },
            { "test_refcount2", foo_bar, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        assert module.test_refcount()
        assert module.test_refcount2()


    def test_init_exception(self):
        import sys
        init = """
            PyErr_SetString(PyExc_Exception, "moo!");
        """
        exc = raises(Exception, "self.import_module(name='foo', init=init)")
        if type(exc.value) is not Exception:
            raise exc.value

        assert exc.value.message == "moo!"


    def test_internal_exceptions(self):
        import sys
        init = """
        if (Py_IsInitialized())
            Py_InitModule("foo", methods);
        """
        body = """
        PyAPI_FUNC(PyObject*) PyPy_Crash1(void);
        PyAPI_FUNC(long) PyPy_Crash2(void);
        static PyObject* foo_crash1(PyObject* self, PyObject *args)
        {
            return PyPy_Crash1();
        }
        static PyObject* foo_crash2(PyObject* self, PyObject *args)
        {
            int a = PyPy_Crash2();
            if (a == -1)
                return NULL;
            return PyFloat_FromDouble(a);
        }
        static PyObject* foo_crash3(PyObject* self, PyObject *args)
        {
            int a = PyPy_Crash2();
            if (a == -1)
                PyErr_Clear();
            return PyFloat_FromDouble(a);
        }
        static PyObject* foo_crash4(PyObject* self, PyObject *args)
        {
            int a = PyPy_Crash2();
            return PyFloat_FromDouble(a);
        }
        static PyObject* foo_clear(PyObject* self, PyObject *args)
        {
            PyErr_Clear();
            return NULL;
        }
        static PyMethodDef methods[] = {
            { "crash1", foo_crash1, METH_NOARGS },
            { "crash2", foo_crash2, METH_NOARGS },
            { "crash3", foo_crash3, METH_NOARGS },
            { "crash4", foo_crash4, METH_NOARGS },
            { "clear",  foo_clear, METH_NOARGS },
            { NULL }
        };
        """
        module = self.import_module(name='foo', init=init, body=body)
        # uncaught interplevel exceptions are turned into SystemError
        raises(SystemError, module.crash1)
        raises(SystemError, module.crash2)
        # caught exception
        assert module.crash3() == -1
        # An exception was set, but function returned a value
        raises(SystemError, module.crash4)
        # No exception set, but NULL returned
        raises(SystemError, module.clear)

    def test_new_exception(self):
        mod = self.import_extension('foo', [
            ('newexc', 'METH_VARARGS',
             '''
             char *name = PyString_AsString(PyTuple_GetItem(args, 0));
             return PyErr_NewException(name, PyTuple_GetItem(args, 1),
                                       PyTuple_GetItem(args, 2));
             '''
             ),
            ])
        raises(SystemError, mod.newexc, "name", Exception, {})

    def test_hash_pointer(self):
        mod = self.import_extension('foo', [
            ('get_hash', 'METH_NOARGS',
             '''
             return PyInt_FromLong(_Py_HashPointer(Py_None));
             '''
             ),
            ])
        h = mod.get_hash()
        assert h != 0
        assert h % 4 == 0 # it's the pointer value

    def test_types(self):
        """test the presence of random types"""

        mod = self.import_extension('foo', [
            ('get_names', 'METH_NOARGS',
             '''
             /* XXX in tests, the C type is not correct */
             #define NAME(type) ((PyTypeObject*)&type)->tp_name
             return Py_BuildValue("sssss",
                                  NAME(PyCell_Type),
                                  NAME(PyModule_Type),
                                  NAME(PyProperty_Type),
                                  NAME(PyStaticMethod_Type),
                                  NAME(PyCFunction_Type)
                                  );
             '''
             ),
            ])
        assert mod.get_names() == ('cell', 'module', 'property',
                                   'staticmethod',
                                   'builtin_function_or_method')

    def test_get_programname(self):
        mod = self.import_extension('foo', [
            ('get_programname', 'METH_NOARGS',
             '''
             char* name1 = Py_GetProgramName();
             char* name2 = Py_GetProgramName();
             if (name1 != name2)
                 Py_RETURN_FALSE;
             return PyString_FromString(name1);
             '''
             ),
            ])
        p = mod.get_programname()
        print p
        assert 'py' in p

    def test_no_double_imports(self):
        import sys, os
        try:
            init = """
            static int _imported_already = 0;
            FILE *f = fopen("_imported_already", "w");
            fprintf(f, "imported_already: %d\\n", _imported_already);
            fclose(f);
            _imported_already = 1;
            if (Py_IsInitialized()) {
                Py_InitModule("foo", NULL);
            }
            """
            self.import_module(name='foo', init=init)
            assert 'foo' in sys.modules

            f = open('_imported_already')
            data = f.read()
            f.close()
            assert data == 'imported_already: 0\n'

            f = open('_imported_already', 'w')
            f.write('not again!\n')
            f.close()
            m1 = sys.modules['foo']
            m2 = self.reimport_module(m1.__file__, name='foo')
            assert m1 is m2
            assert m1 is sys.modules['foo']

            f = open('_imported_already')
            data = f.read()
            f.close()
            assert data == 'not again!\n'

        finally:
            try:
                os.unlink('_imported_already')
            except OSError:
                pass
