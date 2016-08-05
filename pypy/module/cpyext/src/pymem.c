#include <Python.h>

void * PyMem_Malloc(size_t n)
{
    return malloc((n) ? (n) : 1);
}
