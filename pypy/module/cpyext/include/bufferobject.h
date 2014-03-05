
/* Buffer object interface */

/* Note: the object's structure is private */

#ifndef Py_BUFFEROBJECT_H
#define Py_BUFFEROBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
	PyObject_HEAD
	PyObject *b_base;
	void *b_ptr;
	Py_ssize_t b_size;
	Py_ssize_t b_offset;
	int b_readonly;
	long b_hash;
} PyBufferObject;


PyAPI_DATA(PyTypeObject) PyBuffer_Type;

#define PyBuffer_Check(op) (((PyObject*)(op))->ob_type == &PyBuffer_Type)

#define Py_END_OF_BUFFER	(-1)

PyObject* PyBuffer_FromObject(PyObject *base,
                                           Py_ssize_t offset, Py_ssize_t size);
PyObject* PyBuffer_FromReadWriteObject(PyObject *base,
                                                    Py_ssize_t offset,
                                                    Py_ssize_t size);

PyObject* PyBuffer_FromMemory(void *ptr, Py_ssize_t size);
PyObject* PyBuffer_FromReadWriteMemory(void *ptr, Py_ssize_t size);

PyObject* PyBuffer_New(Py_ssize_t size);

PyTypeObject *_Py_get_buffer_type(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_BUFFEROBJECT_H */
