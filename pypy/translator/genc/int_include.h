
/************************************************************/
 /***  C header subsection: operations between ints        ***/


#define OP_INCREF_int(x)          /* nothing */
#define OP_DECREF_int(x)          /* nothing */
#define CONV_TO_OBJ_int           PyInt_FromLong
#define CONV_FROM_OBJ_int         PyInt_AsLong

#define OP_INT_IS_TRUE(x,r,err)   r = (x != 0);

#define OP_INT_ADD(x,y,r,err)     r = x + y;
#define OP_INT_SUB(x,y,r,err)     r = x - y;
