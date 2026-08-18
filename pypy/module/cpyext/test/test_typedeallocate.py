from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase


class AppTestDealloc(AppTestCpythonExtensionBase):
    """Tests that assert *exact* dealloc/GC timing or ordering (call
    counts, list-growth counts, tp_traverse/tp_clear/tp_dealloc call
    order). These are sensitive to whatever garbage is left over from
    prior tests when the shared leak-tracking window gets flushed, so
    they get their own class/file instead of living alongside
    AppTestSlots's much larger, unrelated test population.
    """

    def test_call_tp_dealloc(self):
        module = self.import_extension('foo', [
            ("fetchFooType", "METH_NOARGS",
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
            ("getCounter", "METH_NOARGS",
             """
                return PyLong_FromLong(foo_counter);
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
                Foo_Type.tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE;
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

    def test_heaptype_dealloc(self):
        # Taken from https://github.com/wjakob/pypy_issues at commit 03890103
        import gc
        module = self.import_module(name='nanobind1', filename="nanobind1")
        for i in range(100):
            module.heap_type()
            gc.collect()

    def test_nanobind2_tp_traverse(self):
        # Taken from https://github.com/wjakob/pypy_issues at commit 89a8585
        import gc
        import sys
        if sys.implementation.name == 'pypy':
            skip("tp_traverse not yet implemented in PyPy")
        module = self.import_module(name='nanobind2', filename="nanobind2")
        # Create an unreferenced cycle
        a = module.wrapper()
        a.nested = a
        del a
        for i in range(5):
            gc.collect()
        gl = module.global_list
        assert gl == ['wrapper tp_init called.',
                      'wrapper tp_traverse called.',
                      'wrapper tp_traverse called.',
                      'wrapper tp_clear called.',
                      'wrapper tp_dealloc called.',
                     ]

    def test_nanobind3(self):
        module = self.import_module(name='nanobind3', filename="nanobind3")
        old_list = module.global_list[:]

        o = module.my_object()
        c = module.my_callable()

        with raises(ValueError):
            c(o)

        old_list = module.global_list[:]
        del o
        self.debug_collect()  # will call gc.collect unless run untranslated

        # Make sure o.tp_dealloc was called
        new_list = module.global_list[:]
        assert len(new_list) == len(old_list) + 1, "%s %s" %(old_list, new_list)

    # messes with leak detection, leave at the end of the tests
    def test_tp_new_in_subclass(self):
        import datetime
        module = self.import_module(name='foo3')
        module.footype("X", (object,), {})
        a = module.datetimetype(1, 1, 1)
        assert isinstance(a, module.datetimetype)
