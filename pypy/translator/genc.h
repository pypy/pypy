
/************************************************************/
 /***  Generic C header section                            ***/

#include <Python.h>
#include <structmember.h>


/*** operations on ints ***/

#define OP_LT_iii(x,y,r)           r = x < y;
#define OP_LE_iii(x,y,r)           r = x <= y;
#define OP_EQ_iii(x,y,r)           r = x == y;
#define OP_NE_iii(x,y,r)           r = x != y;
#define OP_GT_iii(x,y,r)           r = x > y;
#define OP_GE_iii(x,y,r)           r = x >= y;

#define OP_IS_TRUE_ii(x,r)         r = !(!x);

#define OP_ADD_iii(x,y,r)          r = x + y;
#define OP_SUB_iii(x,y,r)          r = x - y;
#define OP_MUL_iii(x,y,r)          r = x * y;
#define OP_DIV_iii(x,y,r)          r = x / y;
#define OP_MOD_iii(x,y,r)          r = x % y;
#define OP_INPLACE_ADD_iii(x,y,r)  r = x + y;


/*** generic operations on PyObjects ***/

#define op_richcmp_ooi(x,y,r,err,dir)   \
                       if ((r=PyObject_RichCompareBool(x,y,dir))<0) goto err;
#define OP_LT_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_LT)
#define OP_LE_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_LE)
#define OP_EQ_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_EQ)
#define OP_NE_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_NE)
#define OP_GT_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_GT)
#define OP_GE_ooi(x,y,r,err)  op_richcmp_ooi(x,y,r,err, Py_GE)

#define OP_IS_TRUE_oi(x,r,err)      if ((r=PyObject_IsTrue(x))<0)      goto err;
#define OP_ADD_ooo(x,y,r,err)       if (!(r=PyNumber_Add(x,y)))        goto err;
#define OP_SUB_ooo(x,y,r,err)       if (!(r=PyNumber_Subtract(x,y)))   goto err;
#define OP_MUL_ooo(x,y,r,err)       if (!(r=PyNumber_Multiply(x,y)))   goto err;
#define OP_DIV_ooo(x,y,r,err)       if (!(r=PyNumber_Divide(x,y)))     goto err;
#define OP_MOD_ooo(x,y,r,err)       if (!(r=PyNumber_Remainder(x,y)))  goto err;
#define OP_INPLACE_ADD_ooo(x,y,r,err) if(!(r=PyNumber_InPlaceAdd(x,y)))goto err;

#define OP_GETITEM_ooo(x,y,r,err)   if (!(r=PyObject_GetItem(x,y)))    goto err;
#define OP_SETITEM_ooov(x,y,z,err)  if ((PyObject_SetItem(x,y,z))<0)   goto err;
#define OP_GETATTR_ooo(x,y,r,err)   if (!(r=PyObject_GetAttr(x,y)))    goto err;
#define OP_SETATTR_ooov(x,y,z,err)  if ((PyObject_SetAttr(x,y,z))<0)   goto err;
#define OP_DELATTR_oov(x,y,err)     if ((PyObject_SetAttr(x,y,NULL))<0)goto err;
#define OP_NEWSLICE_oooo(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))    goto err;

/* temporary hack */
#define OP_GETITEM_ooi(x,y,r,err)   {                           \
  PyObject* o = PyObject_GetItem(x,y);                          \
  if (!o) goto err;                                             \
  if ((r=PyInt_AsLong(o)) == -1 && PyErr_Occurred()) goto err;  \
}


/*** conversions ***/

#define convert_io(x,r,err)   if (!(r=PyInt_FromLong(x))) goto err;
#define convert_so(c,l,r,err) if (!(r=PyString_FromStringAndSize(c,l)))goto err;
#define convert_vo(r)         r = Py_None; Py_INCREF(r);

/*#define convert_oi(x,r,err)   if ((r=PyInt_AsLong(x)) == -1             \
 *                                  && PyErr_Occurred()) goto err;
 * -- should be done differently */

/*** tests ***/

#define caseFalse_i(n, err)    if (n) goto err;
#define caseTrue_i(n, err)     if (!n) goto err;
#define case0_i(n, err)        if (n != 0) goto err;
#define case1_i(n, err)        if (n != 1) goto err;

#define caseFalse_o(o, err)    if (!(PyInt_Check(o) && !PyInt_AS_LONG(o))) goto err;
#define caseTrue_o(o, err)     if (!(PyInt_Check(o) && PyInt_AS_LONG(o))) goto err;
#define case0_o(o, err) if (!(PyInt_Check(o) && PyInt_AS_LONG(o)==0)) goto err;
#define case1_o(o, err) if (!(PyInt_Check(o) && PyInt_AS_LONG(o)==1)) goto err;


/*** misc ***/

#define OP_EXCEPTION_ov(x)    /* XXX exceptions not implemented */

#define OP_ALLOC_AND_SET_ioo(l,o,r,err)  {              \
		int i;                                  \
		if (!(r = PyList_New(l))) goto err;     \
		for (i=l; --i >= 0; ) {                 \
			PyList_SET_ITEM(r, i, o);       \
			Py_INCREF(o);                   \
		}                                       \
	}

#define INSTANTIATE(cls, r, err)    if (!(r=cls##_new())) goto err;
#define ALLOC_INSTANCE(cls, r, err)                             \
		if (!(r=PyType_GenericAlloc(&cls##_Type, 0))) goto err;


/* a few built-in functions */

#define CALL_len_oi(o,r,err)  if ((r=PyObject_Size(o))<0) goto err;
#define CALL_pow_iii(x,y,r)   { int i=y; r=1; while (--i>=0) r*=x; } /*slow*/


/************************************************************/
 /***  The rest is produced by genc.py                     ***/
