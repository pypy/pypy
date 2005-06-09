
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/


#define OP_ZERO_MALLOC(size, r, err)  {                 \
    r = (void*) PyObject_Malloc(size);                  \
    if (r == NULL) { PyErr_NoMemory(); FAIL(err) }      \
    memset((void*) r, 0, size);                         \
    COUNT_MALLOC                                        \
  }

#define OP_FREE(p)	{ PyObject_Free(p); COUNT_FREE }


/*------------------------------------------------------------*/
#ifndef COUNT_OP_MALLOCS
/*------------------------------------------------------------*/

#define COUNT_MALLOC	/* nothing */
#define COUNT_FREE	/* nothing */

/*------------------------------------------------------------*/
#else /*COUNT_OP_MALLOCS*/
/*------------------------------------------------------------*/

static int count_mallocs=0, count_frees=0;

#define COUNT_MALLOC	count_mallocs++;
#define COUNT_FREE	count_frees++;

PyObject* malloc_counters(PyObject* self, PyObject* args)
{
  return Py_BuildValue("ii", count_mallocs, count_frees);
}

/*------------------------------------------------------------*/
#endif /*COUNT_OP_MALLOCS*/
/*------------------------------------------------------------*/
