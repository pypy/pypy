#ifndef Py_OBJECT_H
#define Py_OBJECT_H

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_object.h"

#define PY_SSIZE_T_MAX ((Py_ssize_t)(((size_t)-1)>>1))
#define PY_SSIZE_T_MIN (-PY_SSIZE_T_MAX-1)

#define Py_RETURN_NONE return Py_INCREF(Py_None), Py_None

/*
CPython has this for backwards compatibility with really old extensions, and now
we have it for compatibility with CPython.
*/
#define staticforward static

#define PyObject_HEAD_INIT(type)	\
	1, 0, type,

#define PyVarObject_HEAD_INIT(type, size)	\
	PyObject_HEAD_INIT(type) size,

#ifdef PYPY_DEBUG_REFCOUNT
/* Slow version, but useful for debugging */
#define Py_INCREF(ob)   (Py_IncRef((PyObject *)(ob)))
#define Py_DECREF(ob)   (Py_DecRef((PyObject *)(ob)))
#define Py_XINCREF(ob)  (Py_IncRef((PyObject *)(ob)))
#define Py_XDECREF(ob)  (Py_DecRef((PyObject *)(ob)))
#else
/* Fast version */
#define Py_INCREF(ob)   (((PyObject *)(ob))->ob_refcnt++)
#define Py_DECREF(op)                                   \
    do {                                                \
        if (--((PyObject *)(op))->ob_refcnt != 0)       \
            ;                                           \
        else                                            \
            _Py_Dealloc((PyObject *)(op));              \
    } while (0)

#define Py_XINCREF(op) do { if ((op) == NULL) ; else Py_INCREF(op); } while (0)
#define Py_XDECREF(op) do { if ((op) == NULL) ; else Py_DECREF(op); } while (0)
#endif

PyAPI_FUNC(void) Py_IncRef(PyObject *);
PyAPI_FUNC(void) Py_DecRef(PyObject *);
extern void *_pypy_rawrefcount_w_marker_deallocating;
PyAPI_FUNC(void) _Py_Dealloc(PyObject *);

#define Py_CLEAR(op)                        \
        do {                            	\
                if (op) {			\
                        PyObject *_py_tmp = (PyObject *)(op);	\
                        (op) = NULL;		\
                        Py_DECREF(_py_tmp);	\
                }				\
        } while (0)

#define Py_REFCNT(ob)		(((PyObject*)(ob))->ob_refcnt)
#define Py_TYPE(ob)		(((PyObject*)(ob))->ob_type)
#define Py_SIZE(ob)		(((PyVarObject*)(ob))->ob_size)

#define _Py_NewReference(op)                                        \
    ( ((PyObject *)(op))->ob_refcnt = 1,                            \
      ((PyObject *)(op))->ob_pypy_link = 0 )

#define _Py_ForgetReference(ob) /* nothing */

#define Py_None (&_Py_NoneStruct)

/*
Py_NotImplemented is a singleton used to signal that an operation is
not implemented for a given type combination.
*/
#define Py_NotImplemented (&_Py_NotImplementedStruct)

/* Rich comparison opcodes */
/*
    XXX: Also defined in slotdefs.py
*/
#define Py_LT 0
#define Py_LE 1
#define Py_EQ 2
#define Py_NE 3
#define Py_GT 4
#define Py_GE 5

/* Py3k buffer interface, adapted for PyPy */
    /* Flags for getting buffers */
#define PyBUF_SIMPLE 0
#define PyBUF_WRITABLE 0x0001
/*  we used to include an E, backwards compatible alias  */
#define PyBUF_WRITEABLE PyBUF_WRITABLE
#define PyBUF_FORMAT 0x0004
#define PyBUF_ND 0x0008
#define PyBUF_STRIDES (0x0010 | PyBUF_ND)
#define PyBUF_C_CONTIGUOUS (0x0020 | PyBUF_STRIDES)
#define PyBUF_F_CONTIGUOUS (0x0040 | PyBUF_STRIDES)
#define PyBUF_ANY_CONTIGUOUS (0x0080 | PyBUF_STRIDES)
#define PyBUF_INDIRECT (0x0100 | PyBUF_STRIDES)

#define PyBUF_CONTIG (PyBUF_ND | PyBUF_WRITABLE)
#define PyBUF_CONTIG_RO (PyBUF_ND)

#define PyBUF_STRIDED (PyBUF_STRIDES | PyBUF_WRITABLE)
#define PyBUF_STRIDED_RO (PyBUF_STRIDES)

#define PyBUF_RECORDS (PyBUF_STRIDES | PyBUF_WRITABLE | PyBUF_FORMAT)
#define PyBUF_RECORDS_RO (PyBUF_STRIDES | PyBUF_FORMAT)

#define PyBUF_FULL (PyBUF_INDIRECT | PyBUF_WRITABLE | PyBUF_FORMAT)
#define PyBUF_FULL_RO (PyBUF_INDIRECT | PyBUF_FORMAT)


#define PyBUF_READ  0x100
#define PyBUF_WRITE 0x200
#define PyBUF_SHADOW 0x400
/* end Py3k buffer interface */

#define PyObject_Bytes PyObject_Str

/* Flag bits for printing: */
#define Py_PRINT_RAW	1	/* No string quotes etc. */

/*
Type flags (tp_flags)

These flags are used to extend the type structure in a backwards-compatible
fashion. Extensions can use the flags to indicate (and test) when a given
type structure contains a new feature. The Python core will use these when
introducing new functionality between major revisions (to avoid mid-version
changes in the PYTHON_API_VERSION).

Arbitration of the flag bit positions will need to be coordinated among
all extension writers who publically release their extensions (this will
be fewer than you might expect!)..

Python 1.5.2 introduced the bf_getcharbuffer slot into PyBufferProcs.

Type definitions should use Py_TPFLAGS_DEFAULT for their tp_flags value.

Code can use PyType_HasFeature(type_ob, flag_value) to test whether the
given type object has a specified feature.

NOTE: when building the core, Py_TPFLAGS_DEFAULT includes
Py_TPFLAGS_HAVE_VERSION_TAG; outside the core, it doesn't.  This is so
that extensions that modify tp_dict of their own types directly don't
break, since this was allowed in 2.5.  In 3.0 they will have to
manually remove this flag though!
*/

/* PyBufferProcs contains bf_getcharbuffer */
#define Py_TPFLAGS_HAVE_GETCHARBUFFER  (1L<<0)

/* PySequenceMethods contains sq_contains */
#define Py_TPFLAGS_HAVE_SEQUENCE_IN (1L<<1)

/* This is here for backwards compatibility.  Extensions that use the old GC
 * API will still compile but the objects will not be tracked by the GC. */
#define Py_TPFLAGS_GC 0 /* used to be (1L<<2) */

/* PySequenceMethods and PyNumberMethods contain in-place operators */
#define Py_TPFLAGS_HAVE_INPLACEOPS (1L<<3)

/* PyNumberMethods do their own coercion */
#define Py_TPFLAGS_CHECKTYPES (1L<<4)

/* tp_richcompare is defined */
#define Py_TPFLAGS_HAVE_RICHCOMPARE (1L<<5)

/* Objects which are weakly referencable if their tp_weaklistoffset is >0 */
#define Py_TPFLAGS_HAVE_WEAKREFS (1L<<6)

/* tp_iter is defined */
#define Py_TPFLAGS_HAVE_ITER (1L<<7)

/* New members introduced by Python 2.2 exist */
#define Py_TPFLAGS_HAVE_CLASS (1L<<8)

/* Set if the type object is dynamically allocated */
#define Py_TPFLAGS_HEAPTYPE (1L<<9)

/* Set if the type allows subclassing */
#define Py_TPFLAGS_BASETYPE (1L<<10)

/* Set if the type is 'ready' -- fully initialized */
#define Py_TPFLAGS_READY (1L<<12)

/* Set while the type is being 'readied', to prevent recursive ready calls */
#define Py_TPFLAGS_READYING (1L<<13)

/* Objects support garbage collection (see objimp.h) */
#define Py_TPFLAGS_HAVE_GC (1L<<14)

/* These two bits are preserved for Stackless Python, next after this is 17 */
#ifdef STACKLESS
#define Py_TPFLAGS_HAVE_STACKLESS_EXTENSION (3L<<15)
#else
#define Py_TPFLAGS_HAVE_STACKLESS_EXTENSION 0
#endif

/* Objects support nb_index in PyNumberMethods */
#define Py_TPFLAGS_HAVE_INDEX (1L<<17)

/* Objects support type attribute cache */
#define Py_TPFLAGS_HAVE_VERSION_TAG   (1L<<18)
#define Py_TPFLAGS_VALID_VERSION_TAG  (1L<<19)

/* Type is abstract and cannot be instantiated */
#define Py_TPFLAGS_IS_ABSTRACT (1L<<20)

/* Has the new buffer protocol */
#define Py_TPFLAGS_HAVE_NEWBUFFER (1L<<21)

/* These flags are used to determine if a type is a subclass. */
#define Py_TPFLAGS_INT_SUBCLASS		(1L<<23)
#define Py_TPFLAGS_LONG_SUBCLASS	(1L<<24)
#define Py_TPFLAGS_LIST_SUBCLASS	(1L<<25)
#define Py_TPFLAGS_TUPLE_SUBCLASS	(1L<<26)
#define Py_TPFLAGS_STRING_SUBCLASS	(1L<<27)
#define Py_TPFLAGS_UNICODE_SUBCLASS	(1L<<28)
#define Py_TPFLAGS_DICT_SUBCLASS	(1L<<29)
#define Py_TPFLAGS_BASE_EXC_SUBCLASS	(1L<<30)
#define Py_TPFLAGS_TYPE_SUBCLASS	(1L<<31)

/* These are conceptually the same as the flags above, but they are
   PyPy-specific and are stored inside tp_pypy_flags */
#define Py_TPPYPYFLAGS_FLOAT_SUBCLASS (1L<<0)

    
#define Py_TPFLAGS_DEFAULT_EXTERNAL ( \
                             Py_TPFLAGS_HAVE_GETCHARBUFFER | \
                             Py_TPFLAGS_HAVE_SEQUENCE_IN | \
                             Py_TPFLAGS_HAVE_INPLACEOPS | \
                             Py_TPFLAGS_HAVE_RICHCOMPARE | \
                             Py_TPFLAGS_HAVE_WEAKREFS | \
                             Py_TPFLAGS_HAVE_ITER | \
                             Py_TPFLAGS_HAVE_CLASS | \
                             Py_TPFLAGS_HAVE_STACKLESS_EXTENSION | \
                             Py_TPFLAGS_HAVE_INDEX | \
                             0)
#define Py_TPFLAGS_DEFAULT_CORE (Py_TPFLAGS_DEFAULT_EXTERNAL | \
                                 Py_TPFLAGS_HAVE_VERSION_TAG)

#define Py_TPFLAGS_DEFAULT Py_TPFLAGS_DEFAULT_EXTERNAL

#define PyType_HasFeature(t,f)  (((t)->tp_flags & (f)) != 0)
#define PyType_FastSubclass(t,f)  PyType_HasFeature(t,f)

#define _PyPy_Type_FastSubclass(t,f) (((t)->tp_pypy_flags & (f)) != 0)
    
#define PyType_Check(op) \
    PyType_FastSubclass(Py_TYPE(op), Py_TPFLAGS_TYPE_SUBCLASS)
#define PyType_CheckExact(op) (Py_TYPE(op) == &PyType_Type)

/* objimpl.h ----------------------------------------------*/
#define PyObject_New(type, typeobj) \
		( (type *) _PyObject_New(typeobj) )
#define PyObject_NewVar(type, typeobj, n) \
		( (type *) _PyObject_NewVar((typeobj), (n)) )

#define _PyObject_SIZE(typeobj) ( (typeobj)->tp_basicsize )
#define _PyObject_VAR_SIZE(typeobj, nitems)	\
	(size_t)				\
	( ( (typeobj)->tp_basicsize +		\
	    (nitems)*(typeobj)->tp_itemsize +	\
	    (SIZEOF_VOID_P - 1)			\
	  ) & ~(SIZEOF_VOID_P - 1)		\
	)

        
#define PyObject_INIT(op, typeobj) \
    ( Py_TYPE(op) = (typeobj), ((PyObject *)(op))->ob_refcnt = 1,\
      ((PyObject *)(op))->ob_pypy_link = 0, (op) )
#define PyObject_INIT_VAR(op, typeobj, size) \
    ( Py_SIZE(op) = (size), PyObject_INIT((op), (typeobj)) )


PyAPI_FUNC(PyObject *) PyType_GenericAlloc(PyTypeObject *, Py_ssize_t);

/*
#define PyObject_NEW(type, typeobj) \
( (type *) PyObject_Init( \
	(PyObject *) PyObject_MALLOC( _PyObject_SIZE(typeobj) ), (typeobj)) )
*/
#define PyObject_NEW PyObject_New
#define PyObject_NEW_VAR PyObject_NewVar

/*
#define PyObject_NEW_VAR(type, typeobj, n) \
( (type *) PyObject_InitVar( \
      (PyVarObject *) PyObject_MALLOC(_PyObject_VAR_SIZE((typeobj),(n)) ),\
      (typeobj), (n)) )
*/

#define PyObject_GC_New(type, typeobj) \
                ( (type *) _PyObject_GC_New(typeobj) )

#define PyObject_GC_NewVar(type, typeobj, n) \
                ( (type *) _PyObject_GC_NewVar((typeobj), (n)) )
 
/* A dummy PyGC_Head, just to please some tests. Don't use it! */
typedef union _gc_head {
    char dummy;
} PyGC_Head;

/* dummy GC macros */
#define _PyGC_FINALIZED(o) 1
#define PyType_IS_GC(tp) 1

#define PyObject_GC_Track(o)      do { } while(0)
#define PyObject_GC_UnTrack(o)    do { } while(0)
#define _PyObject_GC_TRACK(o)     do { } while(0)
#define _PyObject_GC_UNTRACK(o)   do { } while(0)

/* Utility macro to help write tp_traverse functions.
 * To use this macro, the tp_traverse function must name its arguments
 * "visit" and "arg".  This is intended to keep tp_traverse functions
 * looking as much alike as possible.
 */
#define Py_VISIT(op)                                                    \
        do {                                                            \
                if (op) {                                               \
                        int vret = visit((PyObject *)(op), arg);        \
                        if (vret)                                       \
                                return vret;                            \
                }                                                       \
        } while (0)

#define PyObject_TypeCheck(ob, tp) \
    (Py_TYPE(ob) == (tp) || PyType_IsSubtype(Py_TYPE(ob), (tp)))

#define Py_TRASHCAN_SAFE_BEGIN(pyObj) do {
#define Py_TRASHCAN_SAFE_END(pyObj)   ; } while(0);
/* note: the ";" at the start of Py_TRASHCAN_SAFE_END is needed
   if the code has a label in front of the macro call */

/* Copied from CPython ----------------------------- */
PyAPI_FUNC(int) PyObject_AsReadBuffer(PyObject *, const void **, Py_ssize_t *);
PyAPI_FUNC(int) PyObject_AsWriteBuffer(PyObject *, void **, Py_ssize_t *);
PyAPI_FUNC(int) PyObject_CheckReadBuffer(PyObject *);
PyAPI_FUNC(void *) PyBuffer_GetPointer(Py_buffer *view, Py_ssize_t *indices);
/* Get the memory area pointed to by the indices for the buffer given.
   Note that view->ndim is the assumed size of indices
*/

PyAPI_FUNC(int) PyBuffer_ToContiguous(void *buf, Py_buffer *view,
                                   Py_ssize_t len, char fort);
PyAPI_FUNC(int) PyBuffer_FromContiguous(Py_buffer *view, void *buf,
                                     Py_ssize_t len, char fort);
/* Copy len bytes of data from the contiguous chunk of memory
   pointed to by buf into the buffer exported by obj.  Return
   0 on success and return -1 and raise a PyBuffer_Error on
   error (i.e. the object does not have a buffer interface or
   it is not working).

   If fort is 'F' and the object is multi-dimensional,
   then the data will be copied into the array in
   Fortran-style (first dimension varies the fastest).  If
   fort is 'C', then the data will be copied into the array
   in C-style (last dimension varies the fastest).  If fort
   is 'A', then it does not matter and the copy will be made
   in whatever way is more efficient.

*/


/* on CPython, these are in objimpl.h */

PyAPI_FUNC(void) PyObject_Free(void *);
PyAPI_FUNC(void) PyObject_GC_Del(void *);

#define PyObject_MALLOC         PyObject_Malloc
#define PyObject_REALLOC        PyObject_Realloc
#define PyObject_FREE           PyObject_Free
#define PyObject_Del            PyObject_Free
#define PyObject_DEL            PyObject_Free

PyAPI_FUNC(PyObject *) _PyObject_New(PyTypeObject *);
PyAPI_FUNC(PyVarObject *) _PyObject_NewVar(PyTypeObject *, Py_ssize_t);
PyAPI_FUNC(PyObject *) _PyObject_GC_Malloc(size_t);
PyAPI_FUNC(PyObject *) _PyObject_GC_New(PyTypeObject *);
PyAPI_FUNC(PyVarObject *) _PyObject_GC_NewVar(PyTypeObject *, Py_ssize_t);

PyAPI_FUNC(PyObject *) PyObject_Init(PyObject *, PyTypeObject *);
PyAPI_FUNC(PyVarObject *) PyObject_InitVar(PyVarObject *,
                                           PyTypeObject *, Py_ssize_t);

/*
 * On CPython with Py_REF_DEBUG these use _PyRefTotal, _Py_NegativeRefcount,
 * _Py_GetRefTotal, ...
 * So far we ignore Py_REF_DEBUG
 */

#define _Py_INC_REFTOTAL
#define _Py_DEC_REFTOTAL
#define _Py_REF_DEBUG_COMMA
#define _Py_CHECK_REFCNT(OP)    /* a semicolon */;

/* PyPy internal ----------------------------------- */
PyAPI_FUNC(int) PyPyType_Register(PyTypeObject *);
#define PyObject_Length PyObject_Size
#define _PyObject_GC_Del PyObject_GC_Del
PyAPI_FUNC(void) _PyPy_subtype_dealloc(PyObject *);
PyAPI_FUNC(void) _PyPy_object_dealloc(PyObject *);


#ifdef __cplusplus
}
#endif
#endif /* !Py_OBJECT_H */
