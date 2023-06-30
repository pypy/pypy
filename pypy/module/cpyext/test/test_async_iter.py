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
