
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/


#define OP_ZERO_MALLOC(size, r, err)  {                 \
    r = (void*) PyObject_Malloc(size);                  \
    if (r == NULL) { PyErr_NoMemory(); FAIL(err) }      \
    memset((void*) r, 0, size);                         \
  }

#define OP_FREE(p)	PyObject_Free(p);
