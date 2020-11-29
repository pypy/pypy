#pragma once

/* CPython defines Py_ssize_t in pyport.h as intptr_t */
#ifdef _WIN64
typedef long long Py_ssize_t;
#else
typedef long Py_ssize_t;
#endif

#define PyObject_HEAD  \
    Py_ssize_t ob_refcnt;        \
    Py_ssize_t ob_pypy_link;     \
    struct _typeobject *ob_type;

#define PyObject_VAR_HEAD		\
	PyObject_HEAD			\
	Py_ssize_t ob_size; /* Number of items in variable part */

typedef struct _object {
    PyObject_HEAD
} PyObject;

typedef struct {
	PyObject_VAR_HEAD
} PyVarObject;

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
typedef PyObject *(*intargfunc)(PyObject *, int);
typedef PyObject *(*intintargfunc)(PyObject *, int, int);
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

/* Py3k buffer interface, adapted for PyPy */
/* XXX remove this constant, us a PyObject_VAR_HEAD instead */
#define Py_MAX_NDIMS 36
typedef struct bufferinfo {
    void *buf;
    PyObject *obj;        /* owned reference */
    Py_ssize_t len;

    /* This is Py_ssize_t so it can be
       pointed to by strides in simple case.*/
    Py_ssize_t itemsize;
    int readonly;
    int ndim;
    char *format;
    Py_ssize_t *shape;
    Py_ssize_t *strides;
    Py_ssize_t *suboffsets; /* alway NULL for app-level objects*/
    void *internal; /* always NULL for app-level objects */
    /* PyPy extensions */
    int flags;
    Py_ssize_t _strides[Py_MAX_NDIMS];
    Py_ssize_t _shape[Py_MAX_NDIMS];
    /* static store for shape and strides of
       mono-dimensional buffers. */
    /* Py_ssize_t smalltable[2]; */
} Py_buffer;


typedef int (*getbufferproc)(PyObject *, Py_buffer *, int);
typedef void (*releasebufferproc)(PyObject *, Py_buffer *);
/* end Py3k buffer interface */

typedef int (*objobjproc)(PyObject *, PyObject *);
typedef int (*visitproc)(PyObject *, void *);
typedef int (*traverseproc)(PyObject *, visitproc, void *);

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

/* from methodobject.h */
typedef PyObject *(*PyCFunction)(PyObject *, PyObject *);
typedef PyObject *(*PyCFunctionWithKeywords)(PyObject *, PyObject *,
                                             PyObject *);
typedef PyObject *(*PyNoArgsFunction)(PyObject *);

struct PyMethodDef {
    const char  *ml_name;   /* The name of the built-in function/method */
    PyCFunction  ml_meth;   /* The C function that implements it */
    int          ml_flags;  /* Combination of METH_xxx flags, which mostly
                               describe the args expected by the C func */
    const char  *ml_doc;    /* The __doc__ attribute, or NULL */
};
typedef struct PyMethodDef PyMethodDef;

typedef struct {
    PyObject_HEAD
    PyMethodDef *m_ml; /* Description of the C function to call */
    PyObject    *m_self; /* Passed as 'self' arg to the C func, can be NULL */
    PyObject    *m_module; /* The __module__ attribute, can be anything */
} PyCFunctionObject;

/* from structmember.h */
typedef struct PyMemberDef {
    /* Current version, use this */
    char *name;
    int type;
    Py_ssize_t offset;
    int flags;
    char *doc;
} PyMemberDef;


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

    /* PyPy specific extra fields: make sure that they are ALWAYS at the end,
       for compatibility with CPython */
    long tp_pypy_flags;

} PyTypeObject;

typedef struct _heaptypeobject {
    PyTypeObject ht_type;
    PyNumberMethods as_number;
    PyMappingMethods as_mapping;
    PySequenceMethods as_sequence;
    PyBufferProcs as_buffer;
    PyObject *ht_name, *ht_slots;
} PyHeapTypeObject;
