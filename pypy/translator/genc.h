
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
				  r = NULL;

#define OP_GETATTR(x,y,r,err)     if (!(r=PyObject_GetAttr(x,y)))    goto err;
#define OP_SETATTR(x,y,z,r,err)   if ((PyObject_SetAttr(x,y,z))<0)   goto err; \
				  r = NULL;
#define OP_DELATTR(x,y,r,err)     if ((PyObject_SetAttr(x,y,NULL))<0)goto err; \
				  r = NULL;

#define OP_NEWSLICE(x,y,z,r,err)  if (!(r=PySlice_New(x,y,z)))       goto err;


/*** tests ***/

#define EQ_False(o)     (o == Py_False)
#define EQ_True(o)      (o == Py_True)
#define EQ_0(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==0)
#define EQ_1(o)         (PyInt_Check(o) && PyInt_AS_LONG(o)==1)


/*** misc ***/

#define OP_EXCEPTION(x,r,err)  r = NULL;  /* XXX exceptions not implemented */

#define MOVE(x, y)             y = x;


/************************************************************/
 /***  The rest is produced by genc.py                     ***/
