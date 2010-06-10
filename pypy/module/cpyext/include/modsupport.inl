/* -*- C -*- */
/* Module support interface */

#ifndef Py_MODSUPPORT_INL
#define Py_MODSUPPORT_INL
#ifdef __cplusplus
extern "C" {
#endif

Py_LOCAL_INLINE(PyObject *) Py_InitModule4(
        const char* name, PyMethodDef* methods,
        const char* doc, PyObject *self,
        int api_version)
{
        return _Py_InitPyPyModule(name, methods, doc, self, api_version);
}

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_INL */
