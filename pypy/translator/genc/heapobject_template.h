
/************************************************************/
 /***  C header template: heap object %(typename)s         ***/

/* NB. %(typename)s is the type "pointer to struct s_%(typename)s" */

typedef struct s_%(typename)s {
	%(basestructname)s base;
	%(extensiontypename)s ext;
} *%(typename)s;

#define OP_NEW_%(TYPENAME)s(r,err)  if (!(r=allocate_%(typename)s())) FAIL(err)
#define INIT_HEAPOBJ_%(typename)s(obj) \
		INIT_HEAPOBJ_%(basetypename)s((obj).base)
#define FINI_HEAPOBJ_%(typename)s(obj) \
		FINI_HEAPOBJ_%(basetypename)s((obj).base)
#define REFCNT_%(typename)s(obj) \
		REFCNT_%(basetypename)s((obj).base)

#define OP_INCREF_%(typename)s(x)   REFCNT_%(typename)s(*x)++;
#define OP_DECREF_%(typename)s(x)   if (!--REFCNT_%(typename)s(*x)) \
						dealloc_%(typename)s(x);

static %(typename)s allocate_%(typename)s(void)
{
	%(typename)s result = (%(typename)s)
		PyObject_Malloc(sizeof(struct s_%(typename)s));
	if (result == NULL)
		PyErr_NoMemory();
	INIT_HEAPOBJ_%(typename)s(*result)
	return result;
}

static void dealloc_%(typename)s(%(typename)s obj)
{
	FINI_HEAPOBJ_%(typename)s(*obj)
	PyObject_Free(obj);
}
