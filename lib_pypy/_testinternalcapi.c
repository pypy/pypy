/*
 * C Extension module to test Python internal C APIs (Include/internal).
 */

#if !defined(Py_BUILD_CORE_BUILTIN) && !defined(Py_BUILD_CORE_MODULE)
#  error "Py_BUILD_CORE_BUILTIN or Py_BUILD_CORE_MODULE must be defined"
#endif

/* Always enable assertions */
#undef NDEBUG

#define PY_SSIZE_T_CLEAN

#include "Python.h"
#include "pycore_atomic_funcs.h" // _Py_atomic_int_get()
#include "pycore_bitutils.h"     // _Py_bswap32()
#include "pycore_gc.h"           // PyGC_Head
#include "pycore_hashtable.h"    // _Py_hashtable_new()
#include "pycore_initconfig.h"   // _Py_GetConfigsAsDict()
#include "pycore_interp.h"       // _PyInterpreterState_GetConfigCopy()
#include "pycore_pyerrors.h"      // _Py_UTF8_Edit_Cost()


static PyObject *
get_configs(PyObject *self, PyObject *Py_UNUSED(args))
{
    return _Py_GetConfigsAsDict();
}


static PyObject*
get_recursion_depth(PyObject *self, PyObject *Py_UNUSED(args))
{
    PyThreadState *tstate = PyThreadState_Get();

    /* subtract one to ignore the frame of the get_recursion_depth() call */
    return PyLong_FromLong(tstate->recursion_depth - 1);
}


static PyObject*
test_bswap(PyObject *self, PyObject *Py_UNUSED(args))
{
    uint16_t u16 = _Py_bswap16(UINT16_C(0x3412));
    if (u16 != UINT16_C(0x1234)) {
        PyErr_Format(PyExc_AssertionError,
                     "_Py_bswap16(0x3412) returns %u", u16);
        return NULL;
    }

    uint32_t u32 = _Py_bswap32(UINT32_C(0x78563412));
    if (u32 != UINT32_C(0x12345678)) {
        PyErr_Format(PyExc_AssertionError,
                     "_Py_bswap32(0x78563412) returns %lu", u32);
        return NULL;
    }

    uint64_t u64 = _Py_bswap64(UINT64_C(0xEFCDAB9078563412));
    if (u64 != UINT64_C(0x1234567890ABCDEF)) {
        PyErr_Format(PyExc_AssertionError,
                     "_Py_bswap64(0xEFCDAB9078563412) returns %llu", u64);
        return NULL;
    }

    Py_RETURN_NONE;
}


static int
check_popcount(uint32_t x, int expected)
{
    // Use volatile to prevent the compiler to optimize out the whole test
    volatile uint32_t u = x;
    int bits = _Py_popcount32(u);
    if (bits != expected) {
        PyErr_Format(PyExc_AssertionError,
                     "_Py_popcount32(%lu) returns %i, expected %i",
                     (unsigned long)x, bits, expected);
        return -1;
    }
    return 0;
}


static PyObject*
test_popcount(PyObject *self, PyObject *Py_UNUSED(args))
{
#define CHECK(X, RESULT) \
    do { \
        if (check_popcount(X, RESULT) < 0) { \
            return NULL; \
        } \
    } while (0)

    CHECK(0, 0);
    CHECK(1, 1);
    CHECK(0x08080808, 4);
    CHECK(0x10101010, 4);
    CHECK(0x10204080, 4);
    CHECK(0xDEADCAFE, 22);
    CHECK(0xFFFFFFFF, 32);
    Py_RETURN_NONE;

#undef CHECK
}


static int
check_bit_length(unsigned long x, int expected)
{
    // Use volatile to prevent the compiler to optimize out the whole test
    volatile unsigned long u = x;
    int len = _Py_bit_length(u);
    if (len != expected) {
        PyErr_Format(PyExc_AssertionError,
                     "_Py_bit_length(%lu) returns %i, expected %i",
                     x, len, expected);
        return -1;
    }
    return 0;
}


static PyObject*
test_bit_length(PyObject *self, PyObject *Py_UNUSED(args))
{
#define CHECK(X, RESULT) \
    do { \
        if (check_bit_length(X, RESULT) < 0) { \
            return NULL; \
        } \
    } while (0)

    CHECK(0, 0);
    CHECK(1, 1);
    CHECK(0x1000, 13);
    CHECK(0x1234, 13);
    CHECK(0x54321, 19);
    CHECK(0x7FFFFFFF, 31);
    CHECK(0xFFFFFFFF, 32);
    Py_RETURN_NONE;

#undef CHECK
}


#define TO_PTR(ch) ((void*)(uintptr_t)ch)
#define FROM_PTR(ptr) ((uintptr_t)ptr)
#define VALUE(key) (1 + ((int)(key) - 'a'))

static Py_uhash_t
hash_char(const void *key)
{
    char ch = (char)FROM_PTR(key);
    return ch;
}


static int
hashtable_cb(_Py_hashtable_t *table,
             const void *key_ptr, const void *value_ptr,
             void *user_data)
{
    int *count = (int *)user_data;
    char key = (char)FROM_PTR(key_ptr);
    int value = (int)FROM_PTR(value_ptr);
    assert(value == VALUE(key));
    *count += 1;
    return 0;
}


static PyObject*
test_hashtable(PyObject *self, PyObject *Py_UNUSED(args))
{
    _Py_hashtable_t *table = _Py_hashtable_new(hash_char,
                                               _Py_hashtable_compare_direct);
    if (table == NULL) {
        return PyErr_NoMemory();
    }

    // Using an newly allocated table must not crash
    assert(table->nentries == 0);
    assert(table->nbuckets > 0);
    assert(_Py_hashtable_get(table, TO_PTR('x')) == NULL);

    // Test _Py_hashtable_set()
    char key;
    for (key='a'; key <= 'z'; key++) {
        int value = VALUE(key);
        if (_Py_hashtable_set(table, TO_PTR(key), TO_PTR(value)) < 0) {
            _Py_hashtable_destroy(table);
            return PyErr_NoMemory();
        }
    }
    assert(table->nentries == 26);
    assert(table->nbuckets > table->nentries);

    // Test _Py_hashtable_get_entry()
    for (key='a'; key <= 'z'; key++) {
        _Py_hashtable_entry_t *entry = _Py_hashtable_get_entry(table, TO_PTR(key));
        assert(entry != NULL);
        assert(entry->key == TO_PTR(key));
        assert(entry->value == TO_PTR(VALUE(key)));
    }

    // Test _Py_hashtable_get()
    for (key='a'; key <= 'z'; key++) {
        void *value_ptr = _Py_hashtable_get(table, TO_PTR(key));
        assert((int)FROM_PTR(value_ptr) == VALUE(key));
    }

    // Test _Py_hashtable_steal()
    key = 'p';
    void *value_ptr = _Py_hashtable_steal(table, TO_PTR(key));
    assert((int)FROM_PTR(value_ptr) == VALUE(key));
    assert(table->nentries == 25);
    assert(_Py_hashtable_get_entry(table, TO_PTR(key)) == NULL);

    // Test _Py_hashtable_foreach()
    int count = 0;
    int res = _Py_hashtable_foreach(table, hashtable_cb, &count);
    assert(res == 0);
    assert(count == 25);

    // Test _Py_hashtable_clear()
    _Py_hashtable_clear(table);
    assert(table->nentries == 0);
    assert(table->nbuckets > 0);
    assert(_Py_hashtable_get(table, TO_PTR('x')) == NULL);

    _Py_hashtable_destroy(table);
    Py_RETURN_NONE;
}


static PyObject *
test_get_config(PyObject *Py_UNUSED(self), PyObject *Py_UNUSED(args))
{
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    if (_PyInterpreterState_GetConfigCopy(&config) < 0) {
        PyConfig_Clear(&config);
        return NULL;
    }
    PyObject *dict = _PyConfig_AsDict(&config);
    PyConfig_Clear(&config);
    return dict;
}


static PyObject *
test_set_config(PyObject *Py_UNUSED(self), PyObject *dict)
{
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    if (_PyConfig_FromDict(&config, dict) < 0) {
        goto error;
    }
    if (_PyInterpreterState_SetConfig(&config) < 0) {
        goto error;
    }
    PyConfig_Clear(&config);
    Py_RETURN_NONE;

error:
    PyConfig_Clear(&config);
    return NULL;
}


static PyObject*
test_atomic_funcs(PyObject *self, PyObject *Py_UNUSED(args))
{
    // Test _Py_atomic_size_get() and _Py_atomic_size_set()
    Py_ssize_t var = 1;
    _Py_atomic_size_set(&var, 2);
    assert(_Py_atomic_size_get(&var) == 2);
    Py_RETURN_NONE;
}


static int
check_edit_cost(const char *a, const char *b, Py_ssize_t expected)
{
    int ret = -1;
    PyObject *a_obj = NULL;
    PyObject *b_obj = NULL;

    a_obj = PyUnicode_FromString(a);
    if (a_obj == NULL) {
        goto exit;
    }
    b_obj = PyUnicode_FromString(b);
    if (b_obj == NULL) {
        goto exit;
    }
    Py_ssize_t result = _Py_UTF8_Edit_Cost(a_obj, b_obj, -1);
    if (result != expected) {
        PyErr_Format(PyExc_AssertionError,
                     "Edit cost from '%s' to '%s' returns %zd, expected %zd",
                     a, b, result, expected);
        goto exit;
    }
    // Check that smaller max_edits thresholds are exceeded.
    Py_ssize_t max_edits = result;
    while (max_edits > 0) {
        max_edits /= 2;
        Py_ssize_t result2 = _Py_UTF8_Edit_Cost(a_obj, b_obj, max_edits);
        if (result2 <= max_edits) {
            PyErr_Format(PyExc_AssertionError,
                         "Edit cost from '%s' to '%s' (threshold %zd) "
                         "returns %zd, expected greater than %zd",
                         a, b, max_edits, result2, max_edits);
            goto exit;
        }
    }
    // Check that bigger max_edits thresholds don't change anything
    Py_ssize_t result3 = _Py_UTF8_Edit_Cost(a_obj, b_obj, result * 2 + 1);
    if (result3 != result) {
        PyErr_Format(PyExc_AssertionError,
                     "Edit cost from '%s' to '%s' (threshold %zd) "
                     "returns %zd, expected %zd",
                     a, b, result * 2, result3, result);
        goto exit;
    }
    ret = 0;
exit:
    Py_XDECREF(a_obj);
    Py_XDECREF(b_obj);
    return ret;
}

static PyObject *
test_edit_cost(PyObject *self, PyObject *Py_UNUSED(args))
{
    #define CHECK(a, b, n) do {              \
        if (check_edit_cost(a, b, n) < 0) {  \
            return NULL;                     \
        }                                    \
    } while (0)                              \

    CHECK("", "", 0);
    CHECK("", "a", 2);
    CHECK("a", "A", 1);
    CHECK("Apple", "Aple", 2);
    CHECK("Banana", "B@n@n@", 6);
    CHECK("Cherry", "Cherry!", 2);
    CHECK("---0---", "------", 2);
    CHECK("abc", "y", 6);
    CHECK("aa", "bb", 4);
    CHECK("aaaaa", "AAAAA", 5);
    CHECK("wxyz", "wXyZ", 2);
    CHECK("wxyz", "wXyZ123", 8);
    CHECK("Python", "Java", 12);
    CHECK("Java", "C#", 8);
    CHECK("AbstractFoobarManager", "abstract_foobar_manager", 3+2*2);
    CHECK("CPython", "PyPy", 10);
    CHECK("CPython", "pypy", 11);
    CHECK("AttributeError", "AttributeErrop", 2);
    CHECK("AttributeError", "AttributeErrorTests", 10);

    #undef CHECK
    Py_RETURN_NONE;
}


static PyMethodDef TestMethods[] = {
    {"get_configs", get_configs, METH_NOARGS},
    {"get_recursion_depth", get_recursion_depth, METH_NOARGS},
    {"test_bswap", test_bswap, METH_NOARGS},
    {"test_popcount", test_popcount, METH_NOARGS},
    {"test_bit_length", test_bit_length, METH_NOARGS},
    {"test_hashtable", test_hashtable, METH_NOARGS},
    {"get_config", test_get_config, METH_NOARGS},
    {"set_config", test_set_config, METH_O},
    {"test_atomic_funcs", test_atomic_funcs, METH_NOARGS},
    {"test_edit_cost", test_edit_cost, METH_NOARGS},
    {NULL, NULL} /* sentinel */
};


static struct PyModuleDef _testcapimodule = {
    PyModuleDef_HEAD_INIT,
    "_testinternalcapi",
    NULL,
    -1,
    TestMethods,
    NULL,
    NULL,
    NULL,
    NULL
};


PyMODINIT_FUNC
PyInit__testinternalcapi(void)
{
    PyObject *module = PyModule_Create(&_testcapimodule);
    if (module == NULL) {
        return NULL;
    }

    if (PyModule_AddObject(module, "SIZEOF_PYGC_HEAD",
                           PyLong_FromSsize_t(sizeof(PyGC_Head))) < 0) {
        goto error;
    }

    return module;

error:
    Py_DECREF(module);
    return NULL;
}
