
/************************************************************/
 /***  C header subsection: operations between ints        ***/


#define OP_INT2OBJ(i,r,err)   if (!(r=PyInt_FromLong(i))) FAIL(err)
#define OP_OBJ2INT(o,r,err)   if ((r=PyInt_AsLong(o))==-1 && PyErr_Occurred()) \
							  FAIL(err)

#define OP_NONE2OBJ(n,r,err)  r = Py_None; Py_INCREF(r);
#define OP_OBJ2NONE(o,n,err)  assert(o == Py_None); n = 0;

#define OP_INT_IS_TRUE(x,r,err)   r = (x != 0);

#define OP_INT_ADD(x,y,r,err)     r = x + y;
#define OP_INT_SUB(x,y,r,err)     r = x - y;
