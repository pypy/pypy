/* -*- C -*- */
/* Module support interface */

#ifndef Py_MODSUPPORT_INL
#define Py_MODSUPPORT_INL
#ifdef __cplusplus
extern "C" {
#endif

#ifdef PYPY_STANDALONE
/* XXX1 On translation, forwarddecl.h is included after this file */
/* XXX2 genc.py transforms "const char*" into "char*" */
extern PyObject *_Py_InitPyPyModule(char *, PyMethodDef *, char *, PyObject *, int);
#endif

Py_LOCAL_INLINE(PyObject *) Py_InitModule4(
        const char* name, PyMethodDef* methods,
        const char* doc, PyObject *self,
        int api_version)
{
    return _Py_InitPyPyModule((char*)name, methods,
                              (char*)doc, self,
                              api_version);
}

#ifdef __cplusplus
}
#endif
#endif /* !Py_MODSUPPORT_INL */
