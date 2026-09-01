/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_async_iter.py's
 * test_async_gen_exception_04 actually exercises (see that test's
 * docstring for the original Python source). Compiling this source via
 * PyRun_String at module init avoids hand-rolling the C-level async
 * generator protocol (tp_as_async / __anext__ / __aiter__) by hand.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static const char source[] =
"ZERO = 0\n"
"\n"
"async def gen():\n"
"    yield 123\n"
"    1 / ZERO\n"
"\n"
"def test_last_yield(g):\n"
"    ai = g.__aiter__()\n"
"    an = ai.__anext__()\n"
"    try:\n"
"        next(an)\n"
"    except StopIteration as ex:\n"
"        return ex.args\n"
"    else:\n"
"        return None\n";

static struct PyModuleDef test_async_gen_exception_04_module = {
    PyModuleDef_HEAD_INIT,
    "test_async_gen_exception_04",
    NULL,
    -1,
    NULL,
};

PyMODINIT_FUNC
PyInit_test_async_gen_exception_04(void)
{
    PyObject *m, *moddict, *result;

    m = PyModule_Create(&test_async_gen_exception_04_module);
    if (m == NULL)
        return NULL;

    moddict = PyModule_GetDict(m);
    result = PyRun_String(source, Py_file_input, moddict, moddict);
    if (result == NULL) {
        Py_DECREF(m);
        return NULL;
    }
    Py_DECREF(result);
    return m;
}
