#ifndef Py_ABSTRACTOBJECT_H
#define Py_ABSTRACTOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

     PyAPI_FUNC(int) PyObject_DelItemString(PyObject *o, char *key);

       /*
     Remove the mapping for object, key, from the object *o.
     Returns -1 on failure.  This is equivalent to
     the Python statement: del o[key].
       */


    /* new buffer API */

#define PyObject_CheckBuffer(obj) \
    (((obj)->ob_type->tp_as_buffer != NULL) &&                          \
     (PyType_HasFeature((obj)->ob_type, Py_TPFLAGS_HAVE_NEWBUFFER)) && \
     ((obj)->ob_type->tp_as_buffer->bf_getbuffer != NULL))

    /* Return 1 if the getbuffer function is available, otherwise
       return 0 */

     PyAPI_FUNC(int) PyObject_GetBuffer(PyObject *obj, Py_buffer *view,
                                        int flags);

    /* This is a C-API version of the getbuffer function call.  It checks
       to make sure object has the required function pointer and issues the
       call.  Returns -1 and raises an error on failure and returns 0 on
       success
    */

     PyAPI_FUNC(void) PyBuffer_Release(Py_buffer *view);

       /* Releases a Py_buffer obtained from getbuffer ParseTuple's s*.
    */

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
