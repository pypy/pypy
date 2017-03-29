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


/* Get a pointer to the memoryview's private copy of the exporter's buffer. */
#define PyMemoryView_GET_BUFFER(op) (&((PyMemoryViewObject *)(op))->view)
/* Get a pointer to the exporting object (this may be NULL!). */
#define PyMemoryView_GET_BASE(op) (((PyMemoryViewObject *)(op))->view.obj)


#ifdef __cplusplus
}
#endif
#endif /* !Py_MEMORYOBJECT_H */
