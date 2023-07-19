import pytest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
from pypy.conftest import option


@pytest.mark.skip("too slow, over 30 seconds for this one test")
class AppTestAsyncIter(AppTestCpythonExtensionBase):
    enable_leak_checking = True

    def test_asyncgen(self):
        """ module is this code after running through cython
            async def test_gen():
                a = yield 123
                assert a is None
                yield 456
                yield 789

            def run_until_complete(coro):
                while True:
                    try:
                        fut = coro.send(None)
                    except StopIteration as ex:
                        return ex.args[0]

            def to_list(gen):
                async def iterate():
                    res = []
                    async for i in gen:
                        res.append(i)
                    return res

                return run_until_complete(iterate())
            """
        module = self.import_module(name='test_asyncgen')
        result = module.to_list(module.test_gen())
        assert result == [123, 456, 789]


    def test_async_gen_exception_04(self):
        """module is this code after running through cython, then making some
           small adjustments (see https://github.com/cython/cython/pull/5429)
            ZERO = 0

            async def gen():
                yield 123
                1 / ZERO

            def test_last_yield(g):
                ai = g.__aiter__()
                an = ai.__anext__()
                try:
                    next(an) 
                except StopIteration as ex:
                    return ex.args
                else:
                    return None 
             
        """
        module = self.import_module(name='test_async_gen_exception_04')
        g = module.gen()
        result = module.test_last_yield(g)
        assert result == 123 


class AppTestCoroReturn(AppTestCpythonExtensionBase):
    enable_leak_checking = True

    def test_coro_retval(self):
        """
        # Check that the final result of a coroutine is available in the StopIteration
        # that should be raised by the final call to its tp_iternext method
        body = '''
        static PyObject *value_from_stopiteration()
        {
            PyObject *ptype, *pvalue, *ptraceback, *return_value;
            PyErr_Fetch(&ptype, &pvalue, &ptraceback);
            if (PyErr_GivenExceptionMatches(pvalue, PyExc_StopIteration)) {
                return_value = PyObject_GetAttrString(pvalue, "value");
                Py_XDECREF(pvalue);
            }
            else {
                return_value = pvalue;
            }
            Py_XDECREF(ptype);
            Py_XDECREF(ptraceback);
            return return_value;
        }

        static PyObject *exhaust_coro(PyObject *self, PyObject *args)
        {
            PyObject *coro;
            if (!PyArg_ParseTuple(args, "O", &coro)) {
                return NULL;
            }
            PyObject *coro_wrapper = PyObject_CallMethod(coro, "__await__", NULL);
            if (coro_wrapper == NULL) {
                return NULL;
            }
            PyObject *result;
            iternextfunc next = Py_TYPE(coro_wrapper)->tp_iternext;
            while (1) {
                PyObject *value = next(coro_wrapper);
                if (value) {
                    continue;
                }
                else if (!PyErr_Occurred()) {
                    PyErr_SetString(PyExc_AssertionError, "coroutine finished but there was no exception raised");
                    return NULL;
                }
                else if (!PyErr_ExceptionMatches(PyExc_StopIteration)) {
                    result = NULL;
                }
                else {
                    result = value_from_stopiteration();
                }
                break;
            }

            Py_DECREF(coro_wrapper);
            return result;
        }

        static PyMethodDef methods[] = {
            {"exhaust_coro", exhaust_coro, METH_VARARGS},
            {NULL}
        };

        static struct PyModuleDef moduledef = {
            PyModuleDef_HEAD_INIT, "test_coro_retval", NULL, -1, methods
        };
        '''
        test_coro_retval = self.import_module(name='test_coro_retval', body=body)

        async def test_coro():
            return "hi coro"
        assert test_coro_retval.exhaust_coro(test_coro()) == "hi coro"
        """

    #@pytest.mark.skip("Currently failing, works with CPython")
    def test_coro_written_in_c_retval(self):
        """
        # Check that the final result of a coroutine is available in the StopIteration
        # that should be raised by the final call to its tp_iternext method
        module = self.import_extension('coro_in_c', [
            ("my_awaitable", "METH_NOARGS", '''
                return PyObject_New(PyObject, &MyAwaitable_Type);
            '''),
            ("toggle_build_exception_object", "METH_NOARGS", '''
                _build_exception_object = !_build_exception_object;
                Py_RETURN_NONE;
            '''),
            ("build_exception_object", "METH_NOARGS", '''
                return PyBool_FromLong(_build_exception_object);
            ''')
            ],
            prologue='''
            static int _build_exception_object = 1;
            static PyObject *return_value_via_stopiteration(PyObject *self) {
                if (_build_exception_object) {
                    PyObject *stop_iteration_object = PyObject_CallOneArg(PyExc_StopIteration, PyLong_FromLong(30));
                    PyErr_SetObject(PyExc_StopIteration, stop_iteration_object);
                    Py_DECREF(stop_iteration_object);
                }
                else {
                    PyObject *stop_iteration_args = PyTuple_New(1);
                    PyTuple_SET_ITEM(stop_iteration_args, 0, PyLong_FromLong(30));
                    PyErr_SetObject(PyExc_StopIteration, stop_iteration_args);
                    Py_DECREF(stop_iteration_args);
                }
                return NULL;
            };
            static PyObject *_self(PyObject *self) {
                Py_INCREF(self);
                return self;
            };
            static PyAsyncMethods my_awaitable_async_methods = {
                .am_await = _self,
            };
            PyTypeObject MyAwaitable_Type = {
                PyVarObject_HEAD_INIT(NULL, 0)
                "my_awaitable",
            };
            ''', more_init='''
                MyAwaitable_Type.tp_as_async = &my_awaitable_async_methods;
                MyAwaitable_Type.tp_iter = _self;
                MyAwaitable_Type.tp_iternext = return_value_via_stopiteration;
                if (PyType_Ready(&MyAwaitable_Type) < 0) INITERROR;
            ''')

        import asyncio
        async def arun(coro):
            return await coro

        for _ in range(2):
            print("Trying with build_exception_object = %d" % module.build_exception_object())
            x = asyncio.run(arun(module.my_awaitable()))
            assert x == 30
            module.toggle_build_exception_object();
        """
