import sys
import weakref

import pytest

from pypy.tool.cpyext.extbuild import (
    SystemCompilationInfo, HERE, get_sys_info_app)
from pypy.interpreter.gateway import unwrap_spec, interp2app
from rpython.rtyper.lltypesystem import lltype, ll2ctypes
from pypy.module.cpyext import api
from pypy.module.cpyext.state import State
from rpython.tool.identity_dict import identity_dict
from rpython.tool import leakfinder
from rpython.rlib import rawrefcount
from rpython.tool.udir import udir

only_pypy ="config.option.runappdirect and '__pypy__' not in sys.builtin_module_names"

@api.cpython_api([], api.PyObject)
def PyPy_Crash1(space):
    1/0

@api.cpython_api([], lltype.Signed, error=-1)
def PyPy_Crash2(space):
    1/0

class SpaceCompiler(SystemCompilationInfo):
    """Extension compiler for regular (untranslated PyPy) mode"""
    def __init__(self, space, *args, **kwargs):
        self.space = space
        SystemCompilationInfo.__init__(self, *args, **kwargs)

    def load_module(self, mod, name):
        space = self.space
        api.load_extension_module(space, mod, name)
        return space.getitem(
            space.sys.get('modules'), space.wrap(name))


def get_cpyext_info(space):
    from pypy.module.imp.importing import get_so_extension
    state = space.fromcache(State)
    api_library = state.api_lib
    if sys.platform == 'win32':
        libraries = [api_library]
        # '%s' undefined; assuming extern returning int
        compile_extra = ["/we4013"]
        # prevent linking with PythonXX.lib
        w_maj, w_min = space.fixedview(space.sys.get('version_info'), 5)[:2]
        link_extra = ["/NODEFAULTLIB:Python%d%d.lib" %
            (space.int_w(w_maj), space.int_w(w_min))]
    else:
        libraries = []
        if sys.platform.startswith('linux'):
            compile_extra = [
                "-Werror", "-g", "-O0", "-Wp,-U_FORTIFY_SOURCE", "-fPIC"]
            link_extra = ["-g"]
        else:
            compile_extra = link_extra = None
    return SpaceCompiler(space,
        builddir_base=udir,
        include_extra=api.include_dirs,
        compile_extra=compile_extra,
        link_extra=link_extra,
        extra_libs=libraries,
        ext=get_so_extension(space))


def freeze_refcnts(self):
    rawrefcount._dont_free_any_more()
    return #ZZZ
    state = self.space.fromcache(RefcountState)
    self.frozen_refcounts = {}
    for w_obj, obj in state.py_objects_w2r.iteritems():
        self.frozen_refcounts[w_obj] = obj.c_ob_refcnt
    #state.print_refcounts()
    self.frozen_ll2callocations = set(ll2ctypes.ALLOCATED.values())

class LeakCheckingTest(object):
    """Base class for all cpyext tests."""
    spaceconfig = dict(usemodules=['cpyext', 'thread', 'struct', 'array',
                                   'itertools', 'time', 'binascii',
                                   'micronumpy', 'mmap'
                                   ])

    enable_leak_checking = True

    @staticmethod
    def cleanup_references(space):
        return #ZZZ
        state = space.fromcache(RefcountState)

        import gc; gc.collect()
        # Clear all lifelines, objects won't resurrect
        for w_obj, obj in state.lifeline_dict._dict.items():
            if w_obj not in state.py_objects_w2r:
                state.lifeline_dict.set(w_obj, None)
            del obj
        import gc; gc.collect()


        for w_obj in state.non_heaptypes_w:
            w_obj.c_ob_refcnt -= 1
        state.non_heaptypes_w[:] = []
        state.reset_borrowed_references()

    def check_and_print_leaks(self):
        rawrefcount._collect()
        # check for sane refcnts
        import gc

        if 1:  #ZZZ  not self.enable_leak_checking:
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
                            except TypeError as e:
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

class AppTestApi(LeakCheckingTest):
    def setup_class(cls):
        from rpython.rlib.clibffi import get_libc_name
        if cls.runappdirect:
            cls.libc = get_libc_name()
        else:
            cls.w_libc = cls.space.wrap(get_libc_name())

    def setup_method(self, meth):
        if not self.runappdirect:
            freeze_refcnts(self)

    def teardown_method(self, meth):
        if self.runappdirect:
            return
        self.space.getexecutioncontext().cleanup_cpyext_state()
        self.cleanup_references(self.space)
        # XXX: like AppTestCpythonExtensionBase.teardown_method:
        # find out how to disable check_and_print_leaks() if the
        # test failed
        assert not self.check_and_print_leaks(), (
            "Test leaks or loses object(s).  You should also check if "
            "the test actually passed in the first place; if it failed "
            "it is likely to reach this place.")


def _unwrap_include_dirs(space, w_include_dirs):
    if w_include_dirs is None:
        return None
    else:
        return [space.str_w(s) for s in space.listview(w_include_dirs)]

def debug_collect(space):
    rawrefcount._collect()

class AppTestCpythonExtensionBase(LeakCheckingTest):

    def setup_class(cls):
        space = cls.space
        cls.w_here = space.wrap(str(HERE))
        cls.w_udir = space.wrap(str(udir))
        cls.w_runappdirect = space.wrap(cls.runappdirect)
        if not cls.runappdirect:
            cls.sys_info = get_cpyext_info(space)
            space.getbuiltinmodule("cpyext")
            # 'import os' to warm up reference counts
            w_import = space.builtin.getdictvalue(space, '__import__')
            space.call_function(w_import, space.wrap("os"))
            #state = cls.space.fromcache(RefcountState) ZZZ
            #state.non_heaptypes_w[:] = []
            cls.w_debug_collect = space.wrap(interp2app(debug_collect))
        else:
            def w_import_module(self, name, init=None, body='', filename=None,
                    include_dirs=None, PY_SSIZE_T_CLEAN=False):
                from extbuild import get_sys_info_app
                sys_info = get_sys_info_app(self.udir)
                return sys_info.import_module(
                    name, init=init, body=body, filename=filename,
                    include_dirs=include_dirs,
                    PY_SSIZE_T_CLEAN=PY_SSIZE_T_CLEAN)
            cls.w_import_module = w_import_module

            def w_import_extension(self, modname, functions, prologue="",
                include_dirs=None, more_init="", PY_SSIZE_T_CLEAN=False):
                from extbuild import get_sys_info_app
                sys_info = get_sys_info_app(self.udir)
                return sys_info.import_extension(
                    modname, functions, prologue=prologue,
                    include_dirs=include_dirs, more_init=more_init,
                    PY_SSIZE_T_CLEAN=PY_SSIZE_T_CLEAN)
            cls.w_import_extension = w_import_extension

            def w_compile_module(self, name,
                    source_files=None, source_strings=None):
                from extbuild import get_sys_info_app
                sys_info = get_sys_info_app(self.udir)
                return sys_info.compile_extension_module(name,
                    source_files=source_files, source_strings=source_strings)
            cls.w_compile_module = w_compile_module

            def w_load_module(self, mod, name):
                from extbuild import get_sys_info_app
                sys_info = get_sys_info_app(self.udir)
                return sys_info.load_module(mod, name)
            cls.w_load_module = w_load_module

            def w_debug_collect(self):
                import gc
                gc.collect()
                gc.collect()
                gc.collect()
            cls.w_debug_collect = w_debug_collect


    def record_imported_module(self, name):
        """
        Record a module imported in a test so that it can be cleaned up in
        teardown before the check for leaks is done.

        name gives the name of the module in the space's sys.modules.
        """
        self.imported_module_names.append(name)

    def setup_method(self, func):
        if self.runappdirect:
            return

        @unwrap_spec(name='text')
        def compile_module(space, name,
                           w_source_files=None,
                           w_source_strings=None):
            """
            Build an extension module linked against the cpyext api library.
            """
            if not space.is_none(w_source_files):
                source_files = space.listview_bytes(w_source_files)
            else:
                source_files = None
            if not space.is_none(w_source_strings):
                source_strings = space.listview_bytes(w_source_strings)
            else:
                source_strings = None
            pydname = self.sys_info.compile_extension_module(
                name,
                source_files=source_files,
                source_strings=source_strings)

            # hackish, but tests calling compile_module() always end up
            # importing the result
            self.record_imported_module(name)

            return space.wrap(pydname)

        @unwrap_spec(name='text', init='text_or_none', body='text',
                     filename='fsencode_or_none', PY_SSIZE_T_CLEAN=bool)
        def import_module(space, name, init=None, body='',
                          filename=None, w_include_dirs=None,
                          PY_SSIZE_T_CLEAN=False):
            include_dirs = _unwrap_include_dirs(space, w_include_dirs)
            w_result = self.sys_info.import_module(
                name, init, body, filename, include_dirs, PY_SSIZE_T_CLEAN)
            self.record_imported_module(name)
            return w_result


        @unwrap_spec(mod='text', name='text')
        def load_module(space, mod, name):
            return self.sys_info.load_module(mod, name)

        @unwrap_spec(modname='text', prologue='text',
                             more_init='text', PY_SSIZE_T_CLEAN=bool)
        def import_extension(space, modname, w_functions, prologue="",
                             w_include_dirs=None, more_init="", PY_SSIZE_T_CLEAN=False):
            functions = space.unwrap(w_functions)
            include_dirs = _unwrap_include_dirs(space, w_include_dirs)
            w_result = self.sys_info.import_extension(
                modname, functions, prologue, include_dirs, more_init,
                PY_SSIZE_T_CLEAN)
            self.record_imported_module(modname)
            return w_result

        # A list of modules which the test caused to be imported (in
        # self.space).  These will be cleaned up automatically in teardown.
        self.imported_module_names = []

        wrap = self.space.wrap
        self.w_compile_module = wrap(interp2app(compile_module))
        self.w_load_module = wrap(interp2app(load_module))
        self.w_import_module = wrap(interp2app(import_module))
        self.w_import_extension = wrap(interp2app(import_extension))

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
        if self.runappdirect:
            return
        for name in self.imported_module_names:
            self.unimport_module(name)
        self.space.getexecutioncontext().cleanup_cpyext_state()
        self.cleanup_references(self.space)
        # XXX: find out how to disable check_and_print_leaks() if the
        # test failed...
        assert not self.check_and_print_leaks(), (
            "Test leaks or loses object(s).  You should also check if "
            "the test actually passed in the first place; if it failed "
            "it is likely to reach this place.")

def collect(space):
    import gc
    rawrefcount._collect()
    gc.collect(2)

def print_pyobj_list(space):
    rawrefcount._print_pyobj_list()

class AppTestCpythonExtensionCycleGC(AppTestCpythonExtensionBase):

    def setup_method(self, func):
        if self.runappdirect:
            return

        @unwrap_spec(methods='text')
        def import_cycle_module(space, methods):
            init = """
            if (Py_IsInitialized()) {
                PyObject* m;
                if (PyType_Ready(&CycleType) < 0)
                    return;
                m = Py_InitModule("cycle", module_methods);
                if (m == NULL)
                    return;
                Py_INCREF(&CycleType);
                PyModule_AddObject(m, "Cycle", (PyObject *)&CycleType);
            }
            """
            body = """
            #include <Python.h>
            #include "structmember.h"
            typedef struct {
                PyObject_HEAD
                PyObject *next;
                PyObject *val;
            } Cycle;
            static PyTypeObject CycleType;
            static int Cycle_traverse(Cycle *self, visitproc visit, void *arg)
            {
                int vret;
                if (self->next) {
                    vret = visit(self->next, arg);
                    if (vret != 0)
                        return vret;
                }
                if (self->val) {
                    vret = visit(self->val, arg);
                    if (vret != 0)
                        return vret;
                }
                return 0;
            }
            static int Cycle_clear(Cycle *self)
            {
                PyObject *tmp;
                tmp = self->next;
                self->next = NULL;
                Py_XDECREF(tmp);
                tmp = self->val;
                self->val = NULL;
                Py_XDECREF(tmp);
                return 0;
            }
            static void Cycle_dealloc(Cycle* self)
            {
                Cycle_clear(self);
                Py_TYPE(self)->tp_free((PyObject*)self);
            }
            static PyObject* Cycle_new(PyTypeObject *type, PyObject *args,
                                       PyObject *kwds)
            {
                Cycle *self;
                self = (Cycle *)type->tp_alloc(type, 0);
                if (self != NULL) {
                    self->next = PyString_FromString("");
                    if (self->next == NULL) {
                        Py_DECREF(self);
                        return NULL;
                    }
                }
                PyObject_GC_Track(self);
                return (PyObject *)self;
            }
            static int Cycle_init(Cycle *self, PyObject *args, PyObject *kwds)
            {
                PyObject *next=NULL, *tmp;
                static char *kwlist[] = {"next", NULL};
                if (! PyArg_ParseTupleAndKeywords(args, kwds, "|O", kwlist,
                                                  &next))
                    return -1;
                if (next) {
                    tmp = self->next;
                    Py_INCREF(next);
                    self->next = next;
                    Py_XDECREF(tmp);
                }
                return 0;
            }
            static PyMemberDef Cycle_members[] = {
                {"next", T_OBJECT_EX, offsetof(Cycle, next), 0, "next"},
                {"val", T_OBJECT_EX, offsetof(Cycle, val), 0, "val"},
                {NULL}  /* Sentinel */
            };
            static PyMethodDef Cycle_methods[] = {
                {NULL}  /* Sentinel */
            };
            static PyTypeObject CycleType = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "Cycle.Cycle",             /* tp_name */
                sizeof(Cycle),             /* tp_basicsize */
                0,                         /* tp_itemsize */
                (destructor)Cycle_dealloc, /* tp_dealloc */
                0,                         /* tp_print */
                0,                         /* tp_getattr */
                0,                         /* tp_setattr */
                0,                         /* tp_compare */
                0,                         /* tp_repr */
                0,                         /* tp_as_number */
                0,                         /* tp_as_sequence */
                0,                         /* tp_as_mapping */
                0,                         /* tp_hash */
                0,                         /* tp_call */
                0,                         /* tp_str */
                0,                         /* tp_getattro */
                0,                         /* tp_setattro */
                0,                         /* tp_as_buffer */
                Py_TPFLAGS_DEFAULT |
                    Py_TPFLAGS_BASETYPE |
                    Py_TPFLAGS_HAVE_GC,    /* tp_flags */
                "Cycle objects",           /* tp_doc */
                (traverseproc)Cycle_traverse,   /* tp_traverse */
                (inquiry)Cycle_clear,           /* tp_clear */
                0,                         /* tp_richcompare */
                0,                         /* tp_weaklistoffset */
                0,                         /* tp_iter */
                0,                         /* tp_iternext */
                Cycle_methods,             /* tp_methods */
                Cycle_members,             /* tp_members */
                0,                         /* tp_getset */
                0,                         /* tp_base */
                0,                         /* tp_dict */
                0,                         /* tp_descr_get */
                0,                         /* tp_descr_set */
                0,                         /* tp_dictoffset */
                (initproc)Cycle_init,      /* tp_init */
                0,                         /* tp_alloc */
                Cycle_new,                 /* tp_new */
            };
            """
            w_result = self.sys_info.import_module("cycle", init,
                                                   body + methods,
                                                   None, None, False)
            return w_result

        self.imported_module_names = []

        wrap = self.space.wrap
        self.w_import_cycle_module = wrap(interp2app(import_cycle_module))
        self.w_collect = wrap(interp2app(collect))
        self.w_print_pyobj_list = wrap(interp2app(print_pyobj_list))

    # def test_free_self_reference_cycle_child_pypyobj(self):
    #     cycle = self.import_cycle_module("""
    #         static Cycle *c;
    #         static PyObject * Cycle_cc(Cycle *self, PyObject *val)
    #         {
    #             c = PyObject_GC_New(Cycle, &CycleType);
    #             if (c == NULL)
    #                 return NULL;
    #             Py_INCREF(val);
    #             c->val = val;                // set value
    #             Py_INCREF(c);
    #             c->next = (PyObject *)c;     // create self reference
    #             Py_INCREF(Py_None);
    #             return Py_None;
    #         }
    #         static PyObject * Cycle_cd(Cycle *self)
    #         {
    #             Py_DECREF(c);                // throw cycle away
    #             Py_INCREF(Py_None);
    #             return Py_None;
    #         }
    #         static PyMethodDef module_methods[] = {
    #             {"createCycle", (PyCFunction)Cycle_cc, METH_OLDARGS, ""},
    #             {"discardCycle", (PyCFunction)Cycle_cd, METH_NOARGS, ""},
    #             {NULL}  /* Sentinel */
    #         };
    #         """)
    #
    #     class Example(object):
    #         del_called = -1
    #
    #         def __init__(self, val):
    #             self.val = val
    #             Example.del_called = 0
    #
    #         def __del__(self):
    #             Example.del_called = self.val
    #
    #     # don't keep any reference in pypy
    #     cycle.createCycle(Example(42))
    #     self.collect()
    #     assert Example.del_called == 0
    #     cycle.discardCycle()
    #     self.collect()
    #     assert Example.del_called == 42
    #
    #     # keep a temporary reference in pypy
    #     e = Example(43)
    #     cycle.createCycle(e)
    #     cycle.discardCycle()
    #     self.collect()
    #     assert Example.del_called == 0
    #     e = None
    #     self.collect()
    #     assert Example.del_called == 43
    #
    #     # keep a reference in pypy, free afterwards
    #     e = Example(44)
    #     cycle.createCycle(e)
    #     self.collect()
    #     assert Example.del_called == 0
    #     e = None
    #     self.collect()
    #     assert Example.del_called == 0
    #     cycle.discardCycle()
    #     self.collect()
    #     assert Example.del_called == 44
    #
    # def test_free_self_reference_cycle_parent_pypyobj(self):
    #     # create and return a second object which references the cycle, because
    #     # otherwise we will end up with a cycle that spans across cpy/pypy,
    #     # which we don't want to test here
    #     cycle = self.import_cycle_module("""
    #         static PyObject * Cycle_cc(Cycle *self, PyObject *val)
    #         {
    #             Cycle *c = PyObject_GC_New(Cycle, &CycleType);
    #             if (c == NULL)
    #                 return NULL;
    #             Cycle *c2 = PyObject_GC_New(Cycle, &CycleType);
    #             if (c2 == NULL)
    #                 return NULL;
    #             Py_INCREF(val);
    #             c2->val = val;                // set value
    #             Py_INCREF(c2);
    #             c2->next = (PyObject *)c2;    // create self reference
    #             c->next = (PyObject *)c2;
    #             return (PyObject *)c;         // return other object
    #         }
    #         static PyMethodDef module_methods[] = {
    #             {"createCycle", (PyCFunction)Cycle_cc, METH_OLDARGS, ""},
    #             {NULL}  /* Sentinel */
    #         };
    #         """)
    #
    #     class Example(object):
    #         del_called = -1
    #
    #         def __init__(self, val):
    #             self.val = val
    #             Example.del_called = 0
    #
    #         def __del__(self):
    #             Example.del_called = self.val
    #
    #     c = cycle.createCycle(Example(42))
    #     self.collect()
    #     assert Example.del_called == 0
    #     c = None
    #     self.collect()
    #     assert Example.del_called == 42
    #
    # def test_free_simple_cycle_child_pypyobj(self):
    #     cycle = self.import_cycle_module("""
    #         static Cycle *c;
    #         static PyObject * Cycle_cc(Cycle *self, PyObject *val)
    #         {
    #             c = PyObject_GC_New(Cycle, &CycleType);
    #             if (c == NULL)
    #                 return NULL;
    #             Cycle *c2 = PyObject_GC_New(Cycle, &CycleType);
    #             if (c2 == NULL)
    #                 return NULL;
    #             Py_INCREF(val);
    #             c->val = val;                // set value
    #             c->next = (PyObject *)c2;
    #             Py_INCREF(c);
    #             c2->next = (PyObject *)c;    // simple cycle across two objects
    #             Py_INCREF(Py_None);
    #             return Py_None;
    #         }
    #         static PyObject * Cycle_cd(Cycle *self)
    #         {
    #             Py_DECREF(c);                // throw cycle away
    #             Py_INCREF(Py_None);
    #             return Py_None;
    #         }
    #         static PyMethodDef module_methods[] = {
    #             {"createCycle", (PyCFunction)Cycle_cc, METH_OLDARGS, ""},
    #             {"discardCycle", (PyCFunction)Cycle_cd, METH_NOARGS, ""},
    #             {NULL}  /* Sentinel */
    #         };
    #         """)
    #
    #     class Example(object):
    #         del_called = -1
    #
    #         def __init__(self, val):
    #             self.val = val
    #             Example.del_called = 0
    #
    #         def __del__(self):
    #             Example.del_called = self.val
    #
    #     # don't keep any reference in pypy
    #     cycle.createCycle(Example(42))
    #     self.collect()
    #     cycle.discardCycle()
    #     assert Example.del_called == 0
    #     self.collect()
    #     assert Example.del_called == 42
    #
    #     # keep a temporary reference in pypy
    #     e = Example(43)
    #     cycle.createCycle(e)
    #     cycle.discardCycle()
    #     self.collect()
    #     assert Example.del_called == 0
    #     e = None
    #     self.collect()
    #     assert Example.del_called == 43
    #
    #     # keep a reference in pypy, free afterwards
    #     e = Example(44)
    #     cycle.createCycle(e)
    #     self.collect()
    #     assert Example.del_called == 0
    #     e = None
    #     self.collect()
    #     assert Example.del_called == 0
    #     cycle.discardCycle()
    #     self.collect()
    #     assert Example.del_called == 44
    #
    #
    # def test_free_complex_cycle_child_pypyobj(self):
    #     cycle = self.import_cycle_module("""
    #         static PyObject * Cycle_cc(Cycle *self, PyObject *val)
    #         {
    #             Cycle *c = PyObject_GC_New(Cycle, &CycleType);
    #             if (c == NULL)
    #                 return NULL;
    #             Cycle *c2 = PyObject_GC_New(Cycle, &CycleType);
    #             if (c2 == NULL)
    #                 return NULL;
    #             Cycle *c3 = PyObject_GC_New(Cycle, &CycleType);
    #             if (c3 == NULL)
    #                 return NULL;
    #             Py_INCREF(val);
    #             c->val = val;                // set value
    #             Py_INCREF(val);
    #             c3->val = val;                // set value
    #             Py_INCREF(c2);
    #             c->next = (PyObject *)c2;
    #             Py_INCREF(c);
    #             c2->next = (PyObject *)c;    // inner cycle
    #             Py_INCREF(c3);
    #             c2->val = (PyObject *)c3;
    #             Py_INCREF(c);
    #             c3->next = (PyObject *)c;     // outer cycle
    #             Py_DECREF(c);
    #             Py_DECREF(c2);
    #             Py_DECREF(c3);               // throw all objects away
    #             Py_INCREF(Py_None);
    #             return Py_None;
    #         }
    #         static PyMethodDef module_methods[] = {
    #             {"createCycle", (PyCFunction)Cycle_cc, METH_OLDARGS, ""},
    #             {NULL}  /* Sentinel */
    #         };
    #         """)
    #
    #     class Example(object):
    #         del_called = -1
    #
    #         def __init__(self, val):
    #             self.val = val
    #             Example.del_called = 0
    #
    #         def __del__(self):
    #             Example.del_called = self.val
    #
    #     # don't keep any reference in pypy
    #     cycle.createCycle(Example(42))
    #     assert Example.del_called == 0
    #     self.collect()
    #     assert Example.del_called == 42
    #
    #     # keep a temporary reference in pypy
    #     e = Example(43)
    #     cycle.createCycle(e)
    #     e = None
    #     assert Example.del_called == 0
    #     self.collect()
    #     assert Example.del_called == 43
    #
    #     # keep a reference in pypy, free afterwards
    #     e = Example(44)
    #     cycle.createCycle(e)
    #     self.collect()
    #     assert Example.del_called == 0
    #     e = None
    #     self.collect()
    #     assert Example.del_called == 44

    def test_objects_in_global_list(self):
        cycle = self.import_cycle_module("""
            static PyObject * Cycle_Create(Cycle *self, PyObject *val)
            {
                Cycle *c = PyObject_GC_New(Cycle, &CycleType);
                if (c == NULL)
                    return NULL;
                c->next = val;
                return (PyObject *)c;
            }
            static PyMethodDef module_methods[] = {
                {"create", (PyCFunction)Cycle_Create, METH_OLDARGS, ""},
                {NULL}  /* Sentinel */
            };
            """)

        class Example(object):
            def __init__(self, val):
                self.val = val

        c = cycle.create(Example(41))

        self.print_pyobj_list()
        c = cycle.create(Example(42))
        self.print_pyobj_list()

        # TODO: fix rawrefcount, so that the Cycle objects are properly added
        #       to the ALLOCATED list of leakfinder or alternatively not freed
        #       by collect
