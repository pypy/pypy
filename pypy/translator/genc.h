
/************************************************************/
 /***  Generic C header section                            ***/

#include <Python.h>
#include <structmember.h>


#define op_richcmp(x,y,r,err,dir)   \
                       if (!(r=PyObject_RichCompare(x,y,dir))) goto err;
#define OP_LT(x,y,r,err)  op_richcmp(x,y,r,err, Py_LT)
#define OP_LE(x,y,r,err)  op_richcmp(x,y,r,err, Py_LE)
#define OP_EQ(x,y,r,err)  op_richcmp(x,y,r,err, Py_EQ)
#define OP_NE(x,y,r,err)  op_richcmp(x,y,r,err, Py_NE)
#define OP_GT(x,y,r,err)  op_richcmp(x,y,r,err, Py_GT)
#define OP_GE(x,y,r,err)  op_richcmp(x,y,r,err, Py_GE)

#define OP_IS_TRUE(x,r,err)	switch (PyObject_IsTrue(x)) {	\
				case 0: r=Py_False; break;	\
				case 1: r=Py_True;  break;	\
				default: goto err;		\
				}				\
				Py_INCREF(r);

#define OP_ADD(x,y,r,err)         if (!(r=PyNumber_Add(x,y)))        goto err;
#define OP_SUB(x,y,r,err)         if (!(r=PyNumber_Subtract(x,y)))   goto err;
#define OP_MUL(x,y,r,err)         if (!(r=PyNumber_Multiply(x,y)))   goto err;
#define OP_DIV(x,y,r,err)         if (!(r=PyNumber_Divide(x,y)))     goto err;
#define OP_MOD(x,y,r,err)         if (!(r=PyNumber_Remainder(x,y)))  goto err;
#define OP_INPLACE_ADD(x,y,r,err) if(!(r=PyNumber_InPlaceAdd(x,y)))  goto err;

#define OP_GETITEM(x,y,r,err)     if (!(r=PyObject_GetItem(x,y)))    goto err;
#define OP_SETITEM(x,y,z,r,err)   if ((PyObject_SetItem(x,y,z))<0)   goto err; \
				  r=Py_None; Py_INCREF(r);

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    goto err;
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   goto err; \
				  r=Py_None; Py_INCREF(r);
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)goto err; \
				  r=Py_None; Py_INCREF(r);

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       goto err;


/*** tests ***/

#define EQ_False(o)     (o == Py_False)
#define EQ_True(o)      (o == Py_True)
#define EQ_0(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==0)
#define EQ_1(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==1)


/*** misc ***/

  /* XXX exceptions not implemented */
#define OP_EXCEPTION(x,r,err)  r=Py_None; Py_INCREF(r);

#define MOVE(x, y)             y = x;


/*** operations with a variable number of arguments ***/

#define OP_NEWLIST0(r,err)         if (!(r=PyList_New(0))) goto err;
#define OP_NEWLIST(args,r,err)     if (!(r=PyList_Pack args)) goto err;
#define OP_NEWTUPLE(args,r,err)    if (!(r=PyTuple_Pack args)) goto err;
#define OP_SIMPLE_CALL(args,r,err) if (!(r=PyObject_CallFunctionObjArgs args)) \
					goto err;

static PyObject* PyList_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	va_list vargs;

	va_start(vargs, n);
	result = PyList_New(n);
	if (result == NULL)
		return NULL;
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		PyList_SET_ITEM(result, i, o);
	}
	va_end(vargs);
	return result;
}

#if PY_VERSION_HEX < 0x02040000   /* 2.4 */
static PyObject* PyTuple_Pack(int n, ...)
{
	int i;
	PyObject *o;
	PyObject *result;
	PyObject **items;
	va_list vargs;

	va_start(vargs, n);
	result = PyTuple_New(n);
	if (result == NULL)
		return NULL;
	items = ((PyTupleObject *)result)->ob_item;
	for (i = 0; i < n; i++) {
		o = va_arg(vargs, PyObject *);
		Py_INCREF(o);
		items[i] = o;
	}
	va_end(vargs);
	return result;
}
#endif


/************************************************************/
 /***  The rest is produced by genc.py                     ***/
