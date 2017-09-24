/* The struct is declared here but it shouldn't
   be considered public. Don't access those fields directly,
   use the functions instead! */
typedef struct {
    PyObject_HEAD
    Py_buffer view;
} PyMemoryViewObject;
