
/************************************************************/
 /***  C header subsection: support functions              ***/

#define RUNNING_ON_LLINTERP	0
#define OP_JIT_RECORD_KNOWN_CLASS(i, c, r)  /* nothing */

#define FAIL_EXCEPTION(exc, msg) \
	{ \
		RPyRaiseSimpleException(exc, msg); \
	}
#define FAIL_OVF(msg) FAIL_EXCEPTION(PyExc_OverflowError, msg)
#define FAIL_VAL(msg) FAIL_EXCEPTION(PyExc_ValueError, msg)
#define FAIL_ZER(msg) FAIL_EXCEPTION(PyExc_ZeroDivisionError, msg)
#define CFAIL()       RPyConvertExceptionFromCPython()

/* the following macros are used by rpython/lltypesystem/rstr.py */
#define PyString_FromRPyString(rpystr) \
	PyString_FromStringAndSize(_RPyString_AsString(rpystr), RPyString_Size(rpystr))

#define PyUnicode_FromRPyUnicode(rpystr) \
	_PyUnicode_FromRPyUnicode(_RPyUnicode_AsUnicode(rpystr), RPyUnicode_Size(rpystr))

#define PyString_ToRPyString(s, rpystr)                            \
	memcpy(_RPyString_AsString(rpystr), PyString_AS_STRING(s), \
		RPyString_Size(rpystr))

/* Extra checks can be enabled with the RPY_ASSERT or RPY_LL_ASSERT
 * macros.  They differ in the level at which the tests are made.
 * Remember that RPython lists, for example, are implemented as a
 * GcStruct pointing to an over-allocated GcArray.  With RPY_ASSERT you
 * get list index out of bound checks from rlist.py; such tests must be
 * manually written so made we've forgotten a case.  Conversely, with
 * RPY_LL_ASSERT, all GcArray indexing are checked, which is safer
 * against attacks and segfaults - but less precise in the case of
 * lists, because of the overallocated bit.
 *
 * For extra safety, in programs translated with --sandbox we always
 * assume that we want RPY_LL_ASSERT.  You can change it below to trade
 * safety for performance, though the hit is not huge (~10%?).
 */
#ifdef RPY_ASSERT
#  define RPyAssert(x, msg)                                             \
     if (!(x)) RPyAssertFailed(__FILE__, __LINE__, __FUNCTION__, msg)

void RPyAssertFailed(const char* filename, long lineno,
                     const char* function, const char *msg);
#else
#  define RPyAssert(x, msg)   /* nothing */
#endif

void RPyAbort(void);

#if defined(RPY_LL_ASSERT) || defined(RPY_SANDBOXED)
/* obscure macros that can be used as expressions and lvalues to refer
 * to a field of a structure or an item in an array in a "safe" way --
 * they abort() in case of null pointer or out-of-bounds index.  As a
 * speed trade-off, RPyItem actually segfaults if the array is null, but
 * it's a "guaranteed" segfault and not one that can be used by
 * attackers.
 */
#  define RPyCHECK(x)           ((x)?(void)0:RPyAbort())
#  define RPyField(ptr, name)   ((RPyCHECK(ptr), (ptr))->name)
#  define RPyItem(array, index)                                             \
     ((RPyCHECK((index) >= 0 && (index) < (array)->length),                 \
      (array))->items[index])
#  define RPyFxItem(ptr, index, fixedsize)                                  \
     ((RPyCHECK((ptr) && (index) >= 0 && (index) < (fixedsize)),            \
      (ptr))[index])
#  define RPyNLenItem(array, index)                                         \
     ((RPyCHECK((array) && (index) >= 0), (array))->items[index])
#  define RPyBareItem(array, index)                                         \
     ((RPyCHECK((array) && (index) >= 0), (array))[index])

#else
#  define RPyField(ptr, name)                ((ptr)->name)
#  define RPyItem(array, index)              ((array)->items[index])
#  define RPyFxItem(ptr, index, fixedsize)   ((ptr)[index])
#  define RPyNLenItem(array, index)          ((array)->items[index])
#  define RPyBareItem(array, index)          ((array)[index])
#endif

#ifdef PYPY_CPYTHON_EXTENSION

/* prototypes */

PyObject * gencfunc_descr_get(PyObject *func, PyObject *obj, PyObject *type);
PyObject* PyList_Pack(int n, ...);
PyObject* PyDict_Pack(int n, ...);
#if PY_VERSION_HEX < 0x02040000   /* 2.4 */
PyObject* PyTuple_Pack(int n, ...);
#endif
#if PY_VERSION_HEX >= 0x02030000   /* 2.3 */
# define PyObject_GetItem1  PyObject_GetItem
# define PyObject_SetItem1  PyObject_SetItem
#else
PyObject* PyObject_GetItem1(PyObject* obj, PyObject* index);
PyObject* PyObject_SetItem1(PyObject* obj, PyObject* index, PyObject* v);
#endif
PyObject* CallWithShape(PyObject* callable, PyObject* shape, ...);
PyObject* decode_arg(PyObject* fname, int position, PyObject* name,
			    PyObject* vargs, PyObject* vkwds, PyObject* def);
int check_no_more_arg(PyObject* fname, int n, PyObject* vargs);
int check_self_nonzero(PyObject* fname, PyObject* self);
PyObject *PyTuple_GetItem_WithIncref(PyObject *tuple, int index);
int PyTuple_SetItem_WithIncref(PyObject *tuple, int index, PyObject *o);
int PySequence_Contains_with_exc(PyObject *seq, PyObject *ob);
PyObject* _PyUnicode_FromRPyUnicode(wchar_t *items, long length);
#endif  /* PYPY_CPYTHON_EXTENSION */
