
/************************************************************/
 /***  C header subsection: the base (empty) heap object   ***/


typedef struct s_baseobject {
	int refcount;
} *baseobject;

#define OP_NEW_BASEOBJECT(r,err)  if (!(r=allocate_baseobject())) FAIL(err)
#define INIT_HEAPOBJ_baseobject(obj)  (obj).refcount = 1;
#define FINI_HEAPOBJ_baseobject(obj)  ;
#define REFCNT_baseobject(obj)        (obj).refcount

#define OP_INCREF_baseobject(x)   x->refcount++;
#define OP_DECREF_baseobject(x)   if (!--x->refcount) dealloc_baseobject(x);

static baseobject allocate_baseobject(void)
{
	baseobject result = (baseobject)
		PyObject_Malloc(sizeof(struct s_baseobject));
	if (result == NULL)
		PyErr_NoMemory();
	INIT_HEAPOBJ_baseobject(*result)
	return result;
}

static void dealloc_baseobject(baseobject obj)
{
	FINI_HEAPOBJ_baseobject(*obj)
	PyObject_Free(obj);
}
