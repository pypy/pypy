#include <Python.h>

void * PyMem_Malloc(size_t n)
{
		malloc((n) ? (n) : 1);
}
