/* Abstract Object Interface */

#include "Python.h"

/* Shorthands to return certain errors */

static PyObject *
type_error(const char *msg, PyObject *obj)
{
    PyErr_Format(PyExc_TypeError, msg, obj->ob_type->tp_name);
    return NULL;
}

static PyObject *
null_error(void)
{
    if (!PyErr_Occurred())
        PyErr_SetString(PyExc_SystemError,
                        "null argument to internal routine");
    return NULL;
}

/* Operations on any object */

int
PyObject_CheckReadBuffer(PyObject *obj)
{
    PyBufferProcs *pb = obj->ob_type->tp_as_buffer;

    if (pb == NULL ||
        pb->bf_getreadbuffer == NULL ||
        pb->bf_getsegcount == NULL ||
        (*pb->bf_getsegcount)(obj, NULL) != 1)
        return 0;
    return 1;
}

int PyObject_AsReadBuffer(PyObject *obj,
                          const void **buffer,
                          Py_ssize_t *buffer_len)
{
    PyBufferProcs *pb;
    void *pp;
    Py_ssize_t len;

    if (obj == NULL || buffer == NULL || buffer_len == NULL) {
        null_error();
        return -1;
    }
    pb = obj->ob_type->tp_as_buffer;
    if (pb == NULL ||
         pb->bf_getreadbuffer == NULL ||
         pb->bf_getsegcount == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "expected a readable buffer object");
        return -1;
    }
    if ((*pb->bf_getsegcount)(obj, NULL) != 1) {
        PyErr_SetString(PyExc_TypeError,
                        "expected a single-segment buffer object");
        return -1;
    }
    len = (*pb->bf_getreadbuffer)(obj, 0, &pp);
    if (len < 0)
        return -1;
    *buffer = pp;
    *buffer_len = len;
    return 0;
}

int PyObject_AsWriteBuffer(PyObject *obj,
                           void **buffer,
                           Py_ssize_t *buffer_len)
{
    PyBufferProcs *pb;
    void*pp;
    Py_ssize_t len;

    if (obj == NULL || buffer == NULL || buffer_len == NULL) {
        null_error();
        return -1;
    }
    pb = obj->ob_type->tp_as_buffer;
    if (pb == NULL ||
         pb->bf_getwritebuffer == NULL ||
         pb->bf_getsegcount == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "expected a writeable buffer object");
        return -1;
    }
    if ((*pb->bf_getsegcount)(obj, NULL) != 1) {
        PyErr_SetString(PyExc_TypeError,
                        "expected a single-segment buffer object");
        return -1;
    }
    len = (*pb->bf_getwritebuffer)(obj,0,&pp);
    if (len < 0)
        return -1;
    *buffer = pp;
    *buffer_len = len;
    return 0;
}

/* Operations on callable objects */

static PyObject*
call_function_tail(PyObject *callable, PyObject *args)
{
    PyObject *retval;

    if (args == NULL)
        return NULL;

    if (!PyTuple_Check(args)) {
        PyObject *a;

        a = PyTuple_New(1);
        if (a == NULL) {
            Py_DECREF(args);
            return NULL;
        }
        PyTuple_SET_ITEM(a, 0, args);
        args = a;
    }
    retval = PyObject_Call(callable, args, NULL);

    Py_DECREF(args);

    return retval;
}

PyObject *
PyObject_CallFunction(PyObject *callable, const char *format, ...)
{
    va_list va;
    PyObject *args;

    if (callable == NULL)
        return null_error();

    if (format && *format) {
        va_start(va, format);
        args = Py_VaBuildValue(format, va);
        va_end(va);
    }
    else
        args = PyTuple_New(0);

    return call_function_tail(callable, args);
}

PyObject *
_PyObject_CallFunction_SizeT(PyObject *callable, const char *format, ...)
{
    va_list va;
    PyObject *args;

    if (callable == NULL)
        return null_error();

    if (format && *format) {
        va_start(va, format);
        args = _Py_VaBuildValue_SizeT(format, va);
        va_end(va);
    }
    else
        args = PyTuple_New(0);

    return call_function_tail(callable, args);
}

PyObject *
PyObject_CallMethod(PyObject *o, const char *name, const char *format, ...)
{
    va_list va;
    PyObject *args;
    PyObject *func = NULL;
    PyObject *retval = NULL;

    if (o == NULL || name == NULL)
        return null_error();

    func = PyObject_GetAttrString(o, name);
    if (func == NULL) {
        PyErr_SetString(PyExc_AttributeError, name);
        return 0;
    }

    if (!PyCallable_Check(func)) {
        type_error("attribute of type '%.200s' is not callable", func);
        goto exit;
    }

    if (format && *format) {
        va_start(va, format);
        args = Py_VaBuildValue(format, va);
        va_end(va);
    }
    else
        args = PyTuple_New(0);

    retval = call_function_tail(func, args);

  exit:
    /* args gets consumed in call_function_tail */
    Py_XDECREF(func);

    return retval;
}

PyObject *
_PyObject_CallMethod_SizeT(PyObject *o, const char *name, const char *format, ...)
{
    va_list va;
    PyObject *args;
    PyObject *func = NULL;
    PyObject *retval = NULL;

    if (o == NULL || name == NULL)
        return null_error();

    func = PyObject_GetAttrString(o, name);
    if (func == NULL) {
        PyErr_SetString(PyExc_AttributeError, name);
        return 0;
    }

    if (!PyCallable_Check(func)) {
        type_error("attribute of type '%.200s' is not callable", func);
        goto exit;
    }

    if (format && *format) {
        va_start(va, format);
        args = _Py_VaBuildValue_SizeT(format, va);
        va_end(va);
    }
    else
        args = PyTuple_New(0);

    retval = call_function_tail(func, args);

  exit:
    /* args gets consumed in call_function_tail */
    Py_XDECREF(func);

    return retval;
}

static PyObject *
objargs_mktuple(va_list va)
{
    int i, n = 0;
    va_list countva;
    PyObject *result, *tmp;

#ifdef VA_LIST_IS_ARRAY
    memcpy(countva, va, sizeof(va_list));
#else
#ifdef __va_copy
    __va_copy(countva, va);
#else
    countva = va;
#endif
#endif

    while (((PyObject *)va_arg(countva, PyObject *)) != NULL)
        ++n;
    result = PyTuple_New(n);
    if (result != NULL && n > 0) {
        for (i = 0; i < n; ++i) {
            tmp = (PyObject *)va_arg(va, PyObject *);
            Py_INCREF(tmp);
            PyTuple_SET_ITEM(result, i, tmp);
        }
    }
    return result;
}

PyObject *
PyObject_CallMethodObjArgs(PyObject *callable, PyObject *name, ...)
{
    PyObject *args, *tmp;
    va_list vargs;

    if (callable == NULL || name == NULL)
        return null_error();

    callable = PyObject_GetAttr(callable, name);
    if (callable == NULL)
        return NULL;

    /* count the args */
    va_start(vargs, name);
    args = objargs_mktuple(vargs);
    va_end(vargs);
    if (args == NULL) {
        Py_DECREF(callable);
        return NULL;
    }
    tmp = PyObject_Call(callable, args, NULL);
    Py_DECREF(args);
    Py_DECREF(callable);

    return tmp;
}

PyObject *
PyObject_CallFunctionObjArgs(PyObject *callable, ...)
{
    PyObject *args, *tmp;
    va_list vargs;

    if (callable == NULL)
        return null_error();

    /* count the args */
    va_start(vargs, callable);
    args = objargs_mktuple(vargs);
    va_end(vargs);
    if (args == NULL)
        return NULL;
    tmp = PyObject_Call(callable, args, NULL);
    Py_DECREF(args);

    return tmp;
}

/* for binary compatibility with 5.1 */
PyAPI_FUNC(void) PyPyObject_Del(PyObject *);
void PyPyObject_Del(PyObject *op)
{
    PyObject_FREE(op);
}
