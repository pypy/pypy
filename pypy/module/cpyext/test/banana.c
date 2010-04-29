#include "Python.h"

static PyMethodDef banana_functions[] = {
    {NULL, NULL}
};

void initbanana(void)
{
    Py_InitModule("banana", banana_functions);
}
