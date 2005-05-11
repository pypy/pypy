
/************************************************************/
 /***  C header subsection: operations on LowLevelTypes    ***/


/* XXX no reference counting */

#define OP_MALLOC(typename, r, err)                     \
    r = PyObject_Malloc(sizeof(typename));              \
    if (r == NULL) { PyErr_NoMemory(); FAIL(err) }      \
    memset((void*) r, 0, sizeof(typename));

#define OP_GETFIELD(x, fieldname, r, err)         r = x->fieldname;
#define OP_SETFIELD(x, fieldname, val, r, err)    x->fieldname = val;
#define OP_GETSUBSTRUCT(x, fieldname, r, err)     r = &x->fieldname;
