#include <Python.h>

inline
void * PyMem_Malloc(size_t n)
{
		malloc((n) ? (n) : 1);
}
