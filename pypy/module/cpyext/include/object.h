#ifndef Py_OBJECT_H
#define Py_OBJECT_H

#include <stdio.h>


typedef void* Py_buffer;


#define PyObject_HEAD  \
    long obj_refcnt;       \
    struct _object *obj_type;

#define PyObject_VAR_HEAD		\
	PyObject_HEAD			\
	Py_ssize_t obj_size; /* Number of items in variable part */

#define PyObject_HEAD_INIT(type)	\
	1, type,

#define PyVarObject_HEAD_INIT(type, size)	\
	PyObject_HEAD_INIT(type) size,

typedef struct _object {
    PyObject_HEAD
} PyObject;

typedef struct {
	PyObject_VAR_HEAD
} PyVarObject;

#define Py_REFCNT(ob)		(((PyObject*)(ob))->obj_refcnt)
#define Py_TYPE(ob)		(((PyObject*)(ob))->obj_type)
#define Py_SIZE(ob)		(((PyVarObject*)(ob))->obj_size)


extern PyObject *PyPy_None;
#define Py_None PyPy_None

struct _typeobject;
typedef void (*freefunc)(void *);
typedef void (*destructor)(PyObject *);
typedef int (*printfunc)(PyObject *, FILE *, int);
typedef PyObject *(*getattrfunc)(PyObject *, char *);
typedef PyObject *(*getattrofunc)(PyObject *, PyObject *);
typedef int (*setattrfunc)(PyObject *, char *, PyObject *);
typedef int (*setattrofunc)(PyObject *, PyObject *, PyObject *);
typedef int (*cmpfunc)(PyObject *, PyObject *);
typedef PyObject *(*reprfunc)(PyObject *);
typedef long (*hashfunc)(PyObject *);
typedef PyObject *(*richcmpfunc) (PyObject *, PyObject *, int);
typedef PyObject *(*getiterfunc) (PyObject *);
typedef PyObject *(*iternextfunc) (PyObject *);
typedef PyObject *(*descrgetfunc) (PyObject *, PyObject *, PyObject *);
typedef int (*descrsetfunc) (PyObject *, PyObject *, PyObject *);
typedef int (*initproc)(PyObject *, PyObject *, PyObject *);
typedef PyObject *(*newfunc)(struct _typeobject *, PyObject *, PyObject *);
typedef PyObject *(*allocfunc)(struct _typeobject *, Py_ssize_t);

typedef PyObject * (*unaryfunc)(PyObject *);
typedef PyObject * (*binaryfunc)(PyObject *, PyObject *);
typedef PyObject * (*ternaryfunc)(PyObject *, PyObject *, PyObject *);
typedef int (*inquiry)(PyObject *);
typedef Py_ssize_t (*lenfunc)(PyObject *);
typedef int (*coercion)(PyObject **, PyObject **);
typedef PyObject *(*intargfunc)(PyObject *, int) Py_DEPRECATED(2.5);
typedef PyObject *(*intintargfunc)(PyObject *, int, int) Py_DEPRECATED(2.5);
typedef PyObject *(*ssizeargfunc)(PyObject *, Py_ssize_t);
typedef PyObject *(*ssizessizeargfunc)(PyObject *, Py_ssize_t, Py_ssize_t);
typedef int(*intobjargproc)(PyObject *, int, PyObject *);
typedef int(*intintobjargproc)(PyObject *, int, int, PyObject *);
typedef int(*ssizeobjargproc)(PyObject *, Py_ssize_t, PyObject *);
typedef int(*ssizessizeobjargproc)(PyObject *, Py_ssize_t, Py_ssize_t, PyObject *);
typedef int(*objobjargproc)(PyObject *, PyObject *, PyObject *);


/* int-based buffer interface */
typedef int (*getreadbufferproc)(PyObject *, int, void **);
typedef int (*getwritebufferproc)(PyObject *, int, void **);
typedef int (*getsegcountproc)(PyObject *, int *);
typedef int (*getcharbufferproc)(PyObject *, int, char **);
/* ssize_t-based buffer interface */
typedef Py_ssize_t (*readbufferproc)(PyObject *, Py_ssize_t, void **);
typedef Py_ssize_t (*writebufferproc)(PyObject *, Py_ssize_t, void **);
typedef Py_ssize_t (*segcountproc)(PyObject *, Py_ssize_t *);
typedef Py_ssize_t (*charbufferproc)(PyObject *, Py_ssize_t, char **);

typedef int (*objobjproc)(PyObject *, PyObject *);
typedef int (*visitproc)(PyObject *, void *);
typedef int (*traverseproc)(PyObject *, visitproc, void *);

typedef int (*getbufferproc)(PyObject *, Py_buffer *, int);
typedef void (*releasebufferproc)(PyObject *, Py_buffer *);

typedef struct {
	/* For numbers without flag bit Py_TPFLAGS_CHECKTYPES set, all
	   arguments are guaranteed to be of the object's type (modulo
	   coercion hacks -- i.e. if the type's coercion function
	   returns other types, then these are allowed as well).  Numbers that
	   have the Py_TPFLAGS_CHECKTYPES flag bit set should check *both*
	   arguments for proper type and implement the necessary conversions
	   in the slot functions themselves. */

	binaryfunc nb_add;
	binaryfunc nb_subtract;
	binaryfunc nb_multiply;
	binaryfunc nb_divide;
	binaryfunc nb_remainder;
	binaryfunc nb_divmod;
	ternaryfunc nb_power;
	unaryfunc nb_negative;
	unaryfunc nb_positive;
	unaryfunc nb_absolute;
	inquiry nb_nonzero;
	unaryfunc nb_invert;
	binaryfunc nb_lshift;
	binaryfunc nb_rshift;
	binaryfunc nb_and;
	binaryfunc nb_xor;
	binaryfunc nb_or;
	coercion nb_coerce;
	unaryfunc nb_int;
	unaryfunc nb_long;
	unaryfunc nb_float;
	unaryfunc nb_oct;
	unaryfunc nb_hex;
	/* Added in release 2.0 */
	binaryfunc nb_inplace_add;
	binaryfunc nb_inplace_subtract;
	binaryfunc nb_inplace_multiply;
	binaryfunc nb_inplace_divide;
	binaryfunc nb_inplace_remainder;
	ternaryfunc nb_inplace_power;
	binaryfunc nb_inplace_lshift;
	binaryfunc nb_inplace_rshift;
	binaryfunc nb_inplace_and;
	binaryfunc nb_inplace_xor;
	binaryfunc nb_inplace_or;

	/* Added in release 2.2 */
	/* The following require the Py_TPFLAGS_HAVE_CLASS flag */
	binaryfunc nb_floor_divide;
	binaryfunc nb_true_divide;
	binaryfunc nb_inplace_floor_divide;
	binaryfunc nb_inplace_true_divide;

	/* Added in release 2.5 */
	unaryfunc nb_index;
} PyNumberMethods;

typedef struct {
	lenfunc sq_length;
	binaryfunc sq_concat;
	ssizeargfunc sq_repeat;
	ssizeargfunc sq_item;
	ssizessizeargfunc sq_slice;
	ssizeobjargproc sq_ass_item;
	ssizessizeobjargproc sq_ass_slice;
	objobjproc sq_contains;
	/* Added in release 2.0 */
	binaryfunc sq_inplace_concat;
	ssizeargfunc sq_inplace_repeat;
} PySequenceMethods;

typedef struct {
	lenfunc mp_length;
	binaryfunc mp_subscript;
	objobjargproc mp_ass_subscript;
} PyMappingMethods;

typedef struct {
	readbufferproc bf_getreadbuffer;
	writebufferproc bf_getwritebuffer;
	segcountproc bf_getsegcount;
	charbufferproc bf_getcharbuffer;
        getbufferproc bf_getbuffer;
	releasebufferproc bf_releasebuffer;
} PyBufferProcs;



typedef struct _typeobject {
	PyObject_VAR_HEAD
	const char *tp_name; /* For printing, in format "<module>.<name>" */
	Py_ssize_t tp_basicsize, tp_itemsize; /* For allocation */

	/* Methods to implement standard operations */

	destructor tp_dealloc;
	printfunc tp_print;
	getattrfunc tp_getattr;
	setattrfunc tp_setattr;
	cmpfunc tp_compare;
	reprfunc tp_repr;

	/* Method suites for standard classes */

	PyNumberMethods *tp_as_number;
	PySequenceMethods *tp_as_sequence;
	PyMappingMethods *tp_as_mapping;

	/* More standard operations (here for binary compatibility) */

	hashfunc tp_hash;
	ternaryfunc tp_call;
	reprfunc tp_str;
	getattrofunc tp_getattro;
	setattrofunc tp_setattro;

	/* Functions to access object as input/output buffer */
	PyBufferProcs *tp_as_buffer;

	/* Flags to define presence of optional/expanded features */
	long tp_flags;

	const char *tp_doc; /* Documentation string */

	/* Assigned meaning in release 2.0 */
	/* call function for all accessible objects */
	traverseproc tp_traverse;

	/* delete references to contained objects */
	inquiry tp_clear;

	/* Assigned meaning in release 2.1 */
	/* rich comparisons */
	richcmpfunc tp_richcompare;

	/* weak reference enabler */
	Py_ssize_t tp_weaklistoffset;

	/* Added in release 2.2 */
	/* Iterators */
	getiterfunc tp_iter;
	iternextfunc tp_iternext;

	/* Attribute descriptor and subclassing stuff */
	struct PyMethodDef *tp_methods;
	struct PyMemberDef *tp_members;
	struct PyGetSetDef *tp_getset;
	struct _typeobject *tp_base;
	PyObject *tp_dict;
	descrgetfunc tp_descr_get;
	descrsetfunc tp_descr_set;
	Py_ssize_t tp_dictoffset;
	initproc tp_init;
	allocfunc tp_alloc;
	newfunc tp_new;
	freefunc tp_free; /* Low-level free-memory routine */
	inquiry tp_is_gc; /* For PyObject_IS_GC */
	PyObject *tp_bases;
	PyObject *tp_mro; /* method resolution order */
	PyObject *tp_cache;
	PyObject *tp_subclasses;
	PyObject *tp_weaklist;
	destructor tp_del;

	/* Type attribute cache version tag. Added in version 2.6 */
	unsigned int tp_version_tag;

} PyTypeObject;

/*
`Type flags (tp_flags)

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


extern PyTypeObject *PyPyType_Type; /* built-in 'type' */
#define PyType_Type *PyPyType_Type
extern PyTypeObject *PyPyBaseObject_Type;
#define PyBaseObject_Type *PyPyBaseObject_Type
int PyPyType_Ready(PyTypeObject *);
#define PyType_Ready PyPyType_Ready

/* objimpl.h ----------------------------------------------*/

PyObject * _PyObject_New(PyObject *);
// PyVarObject * _PyObject_NewVar(PyTypeObject *, Py_ssize_t);

#define PyObject_New(type, typeobj) \
		( (type *) _PyObject_New(typeobj) )
#define PyObject_NewVar(type, typeobj, n) \
		( (type *) _PyObject_NewVar((typeobj), (n)) )

void PyObject_Del(void *);

/* PyPy internal ----------------------------------- */
int PyPyType_Register(PyTypeObject *);

#endif
