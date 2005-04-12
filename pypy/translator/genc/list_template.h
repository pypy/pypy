
/************************************************************/
 /***  C header template: list structure %(typename)s      ***/

/* NB. list_N is the type "pointer to struct s_list_N" */

typedef struct s_%(typename)s {
	int refcount;
	int count;
	%(itemtypename)s* items;
} *%(typename)s;

static %(typename)s %(typename)s_allocate(int count)
{
	%(typename)s lst = (%(typename)s)
		PyObject_Malloc(sizeof(struct s_%(typename)s));
	if (lst == NULL)
		return (%(typename)s) PyErr_NoMemory();
	lst->refcount = 1;
	lst->count = 0;   /* NOTE! initialized to 0, increase only when
			     real items are put into the list */
	if (count == 0) {
		lst->items = NULL;
	}
	else {
		size_t size = count * sizeof(%(itemtypename)s);
		/* XXX overflow checking? */
		lst->items = (%(itemtypename)s*) PyMem_Malloc(size);
		if (lst->items == NULL) {
			PyObject_Free(lst);
			return (%(typename)s) PyErr_NoMemory();
		}
	}
	return lst;
}

static int %(typename)s_resize(%(typename)s lst, int ncount)
{
	size_t nsize = ncount * sizeof(%(itemtypename)s);
	/* XXX overflow checking? */
	char* p = PyMem_Realloc((char*) lst->items, nsize);
	if (p == NULL) {
		PyErr_NoMemory();
		return -1;
	}
	lst->count = ncount;
	lst->items = (%(itemtypename)s*) p;
	return 0;
}

static void %(typename)s_dealloc(%(typename)s lst)
{
	int i;
	for (i=lst->count; i--; ) {
		OP_DECREF_%(itemtypename)s(lst->items[i])
	}
	PyMem_Free((char*) lst->items);
	PyObject_Free(lst);
}

#define OP_INCREF_%(typename)s(lst)   (lst)->refcount++;
#define OP_DECREF_%(typename)s(lst)   if (!--(lst)->refcount) \
						%(typename)s_dealloc(lst);

/* Cannot convert between representations, because lists are mutable!
   Changes to the original object don't show up in the converted one and
   vice-versa. */

#define CONV_TO_OBJ_%(typename)s     cannot do this!
#define CONV_FROM_OBJ_%(typename)s   cannot do this!

/* static PyObject* CONV_TO_OBJ_%(typename)s(%(typename)s lst) */
/* { */
/* 	int i, n = lst->count; */
/* 	PyObject* result = PyList_New(n); */
/* 	if (result == NULL) return NULL; */
/* 	for (i=0; i<n; i++) { */
/* 		PyObject* o = CONV_TO_OBJ_%(itemtypename)s(lst->items[i]); */
/* 		if (o == NULL) { */
/* 			Py_DECREF(result); */
/* 			return NULL; */
/* 		} */
/* 		PyList_SET_ITEM(result, i, o); */
/* 	} */
/* 	return result; */
/* } */

/* static %(typename)s CONV_FROM_OBJ_%(typename)s(PyObject *lst) */
/* { */
/* 	%(typename)s result; */
/* 	int i, n; */
/* 	n = PyList_Size(lst); */
/* 	if (n < 0) */
/* 		return NULL; */
/* 	result = %(typename)s_allocate(n); */
/* 	if (result == NULL) */
/* 		return NULL; */
/* 	for (i=0; i<n; i++) { */
/* 		result->items[i] = CONV_FROM_OBJ_%(itemtypename)s( */
/* 			PyList_GET_ITEM(lst, i)); */
/* 		if (PyErr_Occurred()) { */
/* 			%(typename)s_dealloc(result); */
/* 			return NULL; */
/* 		} */
/* 		result->count = i+1; */
/* 	} */
/* 	return result; */
/* } */

#define OP_ALLOC_%(TYPENAME)s(n, r, err)  \
			if (!(r=%(typename)s_allocate(n))) FAIL(err)
