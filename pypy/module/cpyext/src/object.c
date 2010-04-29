// contains code from abstract.c
#include <Python.h>


static PyObject *
null_error(void)
{
	if (!PyErr_Occurred())
		PyErr_SetString(PyExc_SystemError,
				"null argument to internal routine");
	return NULL;
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
