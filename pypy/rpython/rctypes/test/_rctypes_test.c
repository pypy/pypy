/* simple test, currently only for structures */
#include <Python.h>
#ifdef MS_WIN32
#include <windows.h>
#endif
#if defined(MS_WIN32) || defined(__CYGWIN__)
#define EXPORT(x) __declspec(dllexport) x
#else
#define EXPORT(x) x
#endif

PyMethodDef module_methods[] = {
	{ NULL, NULL, 0, NULL},
};


typedef struct tagpoint {
	int x;
	int y;
} point;

EXPORT(int) _testfunc_byval(point in, point *pout)
{
    if (pout)
    {
        pout->x = in.x;
        pout->y = in.y;
    }
    return in.x + in.y;
}

EXPORT(void) _testfunc_swap(point *p)
{
    int tmp = p->x;
    p->x = p->y;
    p->y = tmp;
}

EXPORT(int) _testfunc_struct(point in)
{
    return in.x + in.y;
}

EXPORT(point) _testfunc_struct_id(point in)
{
    return in;
}

EXPORT(point*) _testfunc_struct_pointer_id( point* pin )
{
    return pin;
}   

EXPORT(void *) _testfunc_erase_type(void)
{
    static point p;
    p.x = 'x';
    p.y = 'y';
    return (void *)&p;
}

DL_EXPORT(void)
init_rctypes_test(void)
{
    Py_InitModule("_rctypes_test", module_methods);
}

