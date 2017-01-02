#ifndef Py_ABSTRACTOBJECT_H
#define Py_ABSTRACTOBJECT_H

    /* new buffer API */

#define PyObject_CheckBuffer(obj) \
    (((obj)->ob_type->tp_as_buffer != NULL) &&  \
     ((obj)->ob_type->tp_as_buffer->bf_getbuffer != NULL))

    /* Return 1 if the getbuffer function is available, otherwise
       return 0 */

     PyAPI_FUNC(void) PyBuffer_Release(Py_buffer *view);

    /* Releases a Py_buffer obtained from getbuffer ParseTuple's s*.
    */

#endif /* Py_ABSTRACTOBJECT_H */
