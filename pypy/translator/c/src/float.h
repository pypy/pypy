
/************************************************************/
 /***  C header subsection: operations between floats      ***/


/*** unary operations ***/

#define OP_FLOAT_IS_TRUE(x,r)   OP_FLOAT_NE(x,0.0,r)
#define OP_FLOAT_NEG(x,r)       r = -x
#define OP_FLOAT_ABS(x,r)       r = fabs(x)

/***  binary operations ***/

#define OP_FLOAT_EQ(x,y,r)	  r = (x == y)
#define OP_FLOAT_NE(x,y,r)	  r = (x != y)
#define OP_FLOAT_LE(x,y,r)	  r = (x <= y)
#define OP_FLOAT_GT(x,y,r)	  r = (x >  y)
#define OP_FLOAT_LT(x,y,r)	  r = (x <  y)
#define OP_FLOAT_GE(x,y,r)	  r = (x >= y)

#define OP_FLOAT_CMP(x,y,r) \
	r = ((x > y) - (x < y))

/* addition, subtraction */

#define OP_FLOAT_ADD(x,y,r)     r = x + y
#define OP_FLOAT_SUB(x,y,r)     r = x - y
#define OP_FLOAT_MUL(x,y,r)     r = x * y
#define OP_FLOAT_TRUEDIV(x,y,r) r = x / y
#define OP_FLOAT_POW(x,y,r)     r = pow(x, y) 

/*** conversions ***/

#define OP_CAST_FLOAT_TO_INT(x,r)    r = (long)(x)
#define OP_CAST_FLOAT_TO_UINT(x,r)   r = (unsigned long)(x)
#define OP_CAST_INT_TO_FLOAT(x,r)    r = (double)(x)
#define OP_CAST_UINT_TO_FLOAT(x,r)   r = (double)(x)
#define OP_CAST_LONGLONG_TO_FLOAT(x,r) r = (double)(x)
#define OP_CAST_ULONGLONG_TO_FLOAT(x,r) r = (double)(x)
#define OP_CAST_BOOL_TO_FLOAT(x,r)   r = (double)(x)

#ifdef HAVE_LONG_LONG
#define OP_CAST_FLOAT_TO_LONGLONG(x,r) r = (long long)(x)
#define OP_CAST_FLOAT_TO_ULONGLONG(x,r) r = (unsigned long long)(x)
#endif

