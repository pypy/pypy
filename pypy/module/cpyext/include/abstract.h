#ifndef Py_ABSTRACTOBJECT_H
#define Py_ABSTRACTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* === Object Protocol ================================================== */

/* Implemented elsewhere:

   int PyObject_Print(PyObject *o, FILE *fp, int flags);

   Print an object 'o' on file 'fp'.  Returns -1 on error. The flags argument
   is used to enable certain printing options. The only option currently
   supported is Py_Print_RAW.

   (What should be said about Py_Print_RAW?). */


/* Implemented elsewhere:

   int PyObject_HasAttrString(PyObject *o, const char *attr_name);

   Returns 1 if object 'o' has the attribute attr_name, and 0 otherwise.

   This is equivalent to the Python expression: hasattr(o,attr_name).

   This function always succeeds. */


/* Implemented elsewhere:

   PyObject* PyObject_GetAttrString(PyObject *o, const char *attr_name);

   Retrieve an attributed named attr_name form object o.
   Returns the attribute value on success, or NULL on failure.

   This is the equivalent of the Python expression: o.attr_name. */


/* Implemented elsewhere:

   int PyObject_HasAttr(PyObject *o, PyObject *attr_name);

   Returns 1 if o has the attribute attr_name, and 0 otherwise.

   This is equivalent to the Python expression: hasattr(o,attr_name).

   This function always succeeds. */

/* Implemented elsewhere:

   PyObject* PyObject_GetAttr(PyObject *o, PyObject *attr_name);

   Retrieve an attributed named 'attr_name' form object 'o'.
   Returns the attribute value on success, or NULL on failure.

   This is the equivalent of the Python expression: o.attr_name. */


/* Implemented elsewhere:

   int PyObject_SetAttrString(PyObject *o, const char *attr_name, PyObject *v);

   Set the value of the attribute named attr_name, for object 'o',
   to the value 'v'. Raise an exception and return -1 on failure; return 0 on
   success.

   This is the equivalent of the Python statement o.attr_name=v. */


/* Implemented elsewhere:

   int PyObject_SetAttr(PyObject *o, PyObject *attr_name, PyObject *v);

   Set the value of the attribute named attr_name, for object 'o', to the value
   'v'. an exception and return -1 on failure; return 0 on success.

   This is the equivalent of the Python statement o.attr_name=v. */

/* Implemented as a macro:

   int PyObject_DelAttrString(PyObject *o, const char *attr_name);

   Delete attribute named attr_name, for object o. Returns
   -1 on failure.

   This is the equivalent of the Python statement: del o.attr_name. */
#define PyObject_DelAttrString(O,A) PyObject_SetAttrString((O),(A), NULL)


/* Implemented as a macro:

   int PyObject_DelAttr(PyObject *o, PyObject *attr_name);

   Delete attribute named attr_name, for object o. Returns -1
   on failure.  This is the equivalent of the Python
   statement: del o.attr_name. */
#define  PyObject_DelAttr(O,A) PyObject_SetAttr((O),(A), NULL)


/* Implemented elsewhere:

   PyObject *PyObject_Repr(PyObject *o);

   Compute the string representation of object 'o'.  Returns the
   string representation on success, NULL on failure.

   This is the equivalent of the Python expression: repr(o).

   Called by the repr() built-in function. */


/* Implemented elsewhere:

   PyObject *PyObject_Str(PyObject *o);

   Compute the string representation of object, o.  Returns the
   string representation on success, NULL on failure.

   This is the equivalent of the Python expression: str(o).

   Called by the str() and print() built-in functions. */


/* Declared elsewhere

   PyAPI_FUNC(int) PyCallable_Check(PyObject *o);

   Determine if the object, o, is callable.  Return 1 if the object is callable
   and 0 otherwise.

   This function always succeeds. */


#ifdef PY_SSIZE_T_CLEAN
#undef PyObject_CallFunction
#undef PyObject_CallMethod
#define PyObject_CallFunction _PyObject_CallFunction_SizeT
#define PyObject_CallMethod _PyObject_CallMethod_SizeT
#endif


#ifndef PYPY_VERSION
#if !defined(Py_LIMITED_API) || Py_LIMITED_API+0 >= 0x03090000
/* Call a callable Python object without any arguments */
PyAPI_FUNC(PyObject *) PyObject_CallNoArgs(PyObject *func);
#endif
#endif

/* Call a callable Python object 'callable' with arguments given by the
   tuple 'args' and keywords arguments given by the dictionary 'kwargs'.

   'args' must not be NULL, use an empty tuple if no arguments are
   needed. If no named arguments are needed, 'kwargs' can be NULL.

   This is the equivalent of the Python expression:
   callable(*args, **kwargs). */
#ifndef PYPY_VERSION
PyAPI_FUNC(PyObject *) PyObject_Call(PyObject *callable,
                                     PyObject *args, PyObject *kwargs);
#endif

/* Call a callable Python object 'callable', with arguments given by the
   tuple 'args'.  If no arguments are needed, then 'args' can be NULL.

   Returns the result of the call on success, or NULL on failure.

   This is the equivalent of the Python expression:
   callable(*args). */
#ifndef PYPY_VERSION
PyAPI_FUNC(PyObject *) PyObject_CallObject(PyObject *callable,
                                           PyObject *args);
#endif

/* Call a callable Python object, callable, with a variable number of C
   arguments. The C arguments are described using a mkvalue-style format
   string.

   The format may be NULL, indicating that no arguments are provided.

   Returns the result of the call on success, or NULL on failure.

   This is the equivalent of the Python expression:
   callable(arg1, arg2, ...). */
PyAPI_FUNC(PyObject *) PyObject_CallFunction(PyObject *callable,
                                             const char *format, ...);

/* Call the method named 'name' of object 'obj' with a variable number of
   C arguments.  The C arguments are described by a mkvalue format string.

   The format can be NULL, indicating that no arguments are provided.

   Returns the result of the call on success, or NULL on failure.

   This is the equivalent of the Python expression:
   obj.name(arg1, arg2, ...). */
PyAPI_FUNC(PyObject *) PyObject_CallMethod(PyObject *obj,
                                           const char *name,
                                           const char *format, ...);

PyAPI_FUNC(PyObject *) _PyObject_CallFunction_SizeT(PyObject *callable,
                                                    const char *format,
                                                    ...);

PyAPI_FUNC(PyObject *) _PyObject_CallMethod_SizeT(PyObject *obj,
                                                  const char *name,
                                                  const char *format,
                                                  ...);

/* Call a callable Python object 'callable' with a variable number of C
   arguments. The C arguments are provided as PyObject* values, terminated
   by a NULL.

   Returns the result of the call on success, or NULL on failure.

   This is the equivalent of the Python expression:
   callable(arg1, arg2, ...). */
PyAPI_FUNC(PyObject *) PyObject_CallFunctionObjArgs(PyObject *callable,
                                                    ...);

/* Call the method named 'name' of object 'obj' with a variable number of
   C arguments.  The C arguments are provided as PyObject* values, terminated
   by NULL.

   Returns the result of the call on success, or NULL on failure.

   This is the equivalent of the Python expression: obj.name(*args). */

PyAPI_FUNC(PyObject *) PyObject_CallMethodObjArgs(
    PyObject *obj,
    PyObject *name,
    ...);


/* Implemented elsewhere:

   Py_hash_t PyObject_Hash(PyObject *o);

   Compute and return the hash, hash_value, of an object, o.  On
   failure, return -1.

   This is the equivalent of the Python expression: hash(o). */


/* Implemented elsewhere:

   int PyObject_IsTrue(PyObject *o);

   Returns 1 if the object, o, is considered to be true, 0 if o is
   considered to be false and -1 on failure.

   This is equivalent to the Python expression: not not o. */


/* Implemented elsewhere:

   int PyObject_Not(PyObject *o);

   Returns 0 if the object, o, is considered to be true, 1 if o is
   considered to be false and -1 on failure.

   This is equivalent to the Python expression: not o. */


/* Get the type of an object.

   On success, returns a type object corresponding to the object type of object
   'o'. On failure, returns NULL.

   This is equivalent to the Python expression: type(o) */
#ifndef PYPY_VERSION
PyAPI_FUNC(PyObject *) PyObject_Type(PyObject *o);
#endif


/* Return the size of object 'o'.  If the object 'o' provides both sequence and
   mapping protocols, the sequence size is returned.

   On error, -1 is returned.

   This is the equivalent to the Python expression: len(o) */
#ifndef PYPY_VERSION
PyAPI_FUNC(Py_ssize_t) PyObject_Size(PyObject *o);
#endif


/* For DLL compatibility */
#undef PyObject_Length
PyAPI_FUNC(Py_ssize_t) PyObject_Length(PyObject *o);
#define PyObject_Length PyObject_Size


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
