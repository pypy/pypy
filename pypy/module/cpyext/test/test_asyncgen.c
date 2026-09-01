/* Minimal hand-written stand-in for a Cython-compiled extension module.
 * Only implements what pypy/module/cpyext/test/test_async_iter.py's
 * test_asyncgen actually exercises (see that test's docstring for the
 * original Python source). Compiling this source via PyRun_String at
 * module init avoids hand-rolling the C-level async generator protocol
 * (tp_as_async / __anext__ / __aiter__) by hand.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static const char source[] =
"async def test_gen():\n"
"    a = yield 123\n"
"    assert a is None\n"
"    yield 456\n"
"    yield 789\n"
"\n"
"def run_until_complete(coro):\n"
"    while True:\n"
"        try:\n"
"            fut = coro.send(None)\n"
"        except StopIteration as ex:\n"
"            return ex.args[0]\n"
"\n"
"def to_list(gen):\n"
"    async def iterate():\n"
"        res = []\n"
"        async for i in gen:\n"
"            res.append(i)\n"
"        return res\n"
"\n"
"    return run_until_complete(iterate())\n";

static struct PyModuleDef test_asyncgen_module = {
    PyModuleDef_HEAD_INIT,
    "test_asyncgen",
    NULL,
    -1,
    NULL,
};

PyMODINIT_FUNC
PyInit_test_asyncgen(void)
{
    PyObject *m, *moddict, *result;

    m = PyModule_Create(&test_asyncgen_module);
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
