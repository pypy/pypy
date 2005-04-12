
/************************************************************/
 /***  C header subsection: operations between ints        ***/


static PyObject* PyNone_FromInt(int x)
{
	Py_INCREF(Py_None);
	return Py_None;
}

static int PyNone_AsInt(PyObject* o)
{
	if (o != Py_None) {
		PyErr_SetString(PyExc_TypeError, "None expected");
		return -1;
	}
	return 0;
}

static PyObject* PyObject_SameObject(PyObject* obj)
{
	Py_INCREF(obj);
	return obj;
}


#define OP_INT_IS_TRUE(x,r,err)   r = (x != 0);

#define OP_INT_ADD(x,y,r,err)     r = x + y;
#define OP_INT_SUB(x,y,r,err)     r = x - y;
