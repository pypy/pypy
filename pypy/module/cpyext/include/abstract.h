#ifndef Py_ABSTRACTOBJECT_H
#define Py_ABSTRACTOBJECT_H

    /* new buffer API */

#define PyObject_CheckBuffer(obj) \
    (((obj)->ob_type->tp_as_buffer != NULL) &&  \
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

#endif /* Py_ABSTRACTOBJECT_H */
