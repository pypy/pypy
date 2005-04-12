
/************************************************************/
 /***  C header subsection: operations between Nones       ***/

typedef int none;

#define OP_INCREF_none(x)          /* nothing */
#define OP_DECREF_none(x)          /* nothing */


#define CONV_TO_OBJ_none(x)    ((void)Py_INCREF(Py_None), Py_None)

static none CONV_FROM_OBJ_none(PyObject* o)
{
	if (o != Py_None) {
		PyErr_SetString(PyExc_TypeError, "None expected");
		return -1;
	}
	return 0;
}
