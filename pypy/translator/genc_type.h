
/************************************************************/
 /***  C header subsection: typed operations               ***/

/* This file is included from genc.h. */


#define OP_INT2OBJ(i,r,err)   if (!(r=PyInt_FromLong(i))) FAIL(err)
#define OP_OBJ2INT(o,r,err)   if ((r=PyInt_AsLong(o))==-1 && PyErr_Occurred()) \
							  FAIL(err)

#define OP_INT_IS_TRUE(x,r,err)   r = (x != 0);

#define OP_INT_ADD(x,y,r,err)     r = x + y;
#define OP_INT_SUB(x,y,r,err)     r = x - y;
