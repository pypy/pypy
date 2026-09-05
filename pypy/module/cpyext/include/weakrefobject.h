/* Weak references objects for Python. */

#ifndef Py_WEAKREFOBJECT_H
#define Py_WEAKREFOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#define PyWeakref_CheckRef(op) PyObject_TypeCheck((op), &_PyWeakref_RefType)
#define PyWeakref_CheckRefExact(op) \
        Py_IS_TYPE((op), &_PyWeakref_RefType)
#define PyWeakref_CheckProxy(op) \
        (Py_IS_TYPE((op), &_PyWeakref_ProxyType) \
         || Py_IS_TYPE((op), &_PyWeakref_CallableProxyType))

#define PyWeakref_Check(op) \
        (PyWeakref_CheckRef(op) || PyWeakref_CheckProxy(op))

#ifdef __cplusplus
}
#endif
#endif /* !Py_WEAKREFOBJECT_H */
