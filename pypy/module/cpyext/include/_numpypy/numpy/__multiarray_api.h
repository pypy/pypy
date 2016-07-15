

typedef struct {
        PyObject_HEAD
        npy_bool obval;
} PyBoolScalarObject;

#if PY_VERSION_HEX >= 0x03000000
#define NUMPY_IMPORT_ARRAY_RETVAL NULL
#else
#define NUMPY_IMPORT_ARRAY_RETVAL
#endif

#define import_array() {return NUMPY_IMPORT_ARRAY_RETVAL;}


