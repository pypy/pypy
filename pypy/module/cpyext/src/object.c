
#include "Python.h"

int
PyObject_CallFinalizerFromDealloc(PyObject *self)
{
    /* STUB */
    if (self->ob_type->tp_finalize) {
        fprintf(stderr, "WARNING: PyObject_CallFinalizerFromDealloc() "
                        "not implemented (objects of type '%s')\n",
                        self->ob_type->tp_name);
        self->ob_type->tp_finalize = NULL;   /* only once */
    }
    return 0;
}
