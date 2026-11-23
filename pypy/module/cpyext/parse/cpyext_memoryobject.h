/* The struct is declared here but it shouldn't
   be considered public. Don't access those fields directly,
   use the functions instead! */


/* The memoryview is the exporter of view, so it owns the storage that
   view.shape and view.strides point to, like CPython's ob_array */
typedef struct {
    PyObject_HEAD
    Py_buffer view;
    int flags;
    Py_ssize_t _shape[PyBUF_MAX_NDIM];
    Py_ssize_t _strides[PyBUF_MAX_NDIM];
} PyMemoryViewObject;
