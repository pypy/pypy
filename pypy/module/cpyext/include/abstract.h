#ifndef Py_ABSTRACTOBJECT_H
#define Py_ABSTRACTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

     PyAPI_FUNC(int) PyObject_DelItemString(PyObject *o, char *key);
/* === Number Protocol ================================================== */

/* Returns 1 if the object 'o' provides numeric protocols, and 0 otherwise.

   This function always succeeds. */
PyAPI_FUNC(int) PyNumber_Check(PyObject *o);


/* Returns 1 if obj is an index integer (has the nb_index slot of the
   tp_as_number structure filled in), and 0 otherwise. */
PyAPI_FUNC(int) PyIndex_Check(PyObject *);


/* CPython has these in Include/cpython/abstract.h */

#define PY_VECTORCALL_ARGUMENTS_OFFSET ((size_t)1 << (8 * sizeof(size_t) - 1))

static inline Py_ssize_t
PyVectorcall_NARGS(size_t n)
{
    return n & ~PY_VECTORCALL_ARGUMENTS_OFFSET;
}

/* Call "callable" (which must support vectorcall) with positional arguments
   "tuple" and keyword arguments "dict". "dict" may also be NULL */
PyAPI_FUNC(PyObject *) PyVectorcall_Call(PyObject *callable, PyObject *tuple, PyObject *dict);

// Backwards compatibility aliases for API that was provisional in Python 3.8
#define _PyObject_Vectorcall PyObject_Vectorcall
#define _PyObject_VectorcallMethod PyObject_VectorcallMethod
#define _PyObject_FastCallDict PyObject_VectorcallDict
#define _PyVectorcall_Function PyVectorcall_Function
#define _PyObject_CallOneArg PyObject_CallOneArg
#define _PyObject_CallNoArg PyObject_CallNoArgs
#define _PyObject_CallMethodNoArgs PyObject_CallMethodNoArgs
#define _PyObject_CallMethodOneArg PyObject_CallMethodOneArg

/* new buffer API */

/* Return 1 if the getbuffer function is available, otherwise
   return 0 */
#define PyObject_CheckBuffer(obj) \
    (((obj)->ob_type->tp_as_buffer != NULL) &&  \
     ((obj)->ob_type->tp_as_buffer->bf_getbuffer != NULL))


/* This is a C-API version of the getbuffer function call.  It checks
   to make sure object has the required function pointer and issues the
   call.  Returns -1 and raises an error on failure and returns 0 on
   success
*/
PyAPI_FUNC(int) PyObject_GetBuffer(PyObject *obj, Py_buffer *view,
                                    int flags);

/* Releases a Py_buffer obtained from getbuffer ParseTuple's s*.
*/
PyAPI_FUNC(void) PyBuffer_Release(Py_buffer *view);


/*  Mapping protocol:*/

     /* implemented as a macro:

     int PyMapping_DelItemString(PyObject *o, char *key);

     Remove the mapping for object, key, from the object *o.
     Returns -1 on failure.  This is equivalent to
     the Python statement: del o[key].
       */
#define PyMapping_DelItemString(O,K) PyObject_DelItemString((O),(K))

     /* implemented as a macro:

     int PyMapping_DelItem(PyObject *o, PyObject *key);

     Remove the mapping for object, key, from the object *o.
     Returns -1 on failure.  This is equivalent to
     the Python statement: del o[key].
       */
#define PyMapping_DelItem(O,K) PyObject_DelItem((O),(K))

#ifdef __cplusplus
}
#endif
#endif /* Py_ABSTRACTOBJECT_H */
