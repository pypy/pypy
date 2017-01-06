#ifndef Py_MEMORYOBJECT_H
#define Py_MEMORYOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif

/* The struct is declared here but it shouldn't
   be considered public. Don't access those fields directly,
   use the functions instead! */
typedef struct {
    PyObject_HEAD
    Py_buffer view;
} PyMemoryViewObject;




#ifdef __cplusplus
}
#endif
#endif /* !Py_MEMORYOBJECT_H */
