
/************************************************************/
 /***  C header subsection: operations between ints        ***/


#define OP_INCREF_int(x)          /* nothing */
#define OP_DECREF_int(x)          /* nothing */
#define CONV_TO_OBJ_int           PyInt_FromLong
#define CONV_FROM_OBJ_int         PyInt_AS_LONG

#define OP_INT_IS_TRUE(x,r,err)   r = (x != 0);

#define OP_INT_ADD(x,y,r,err)     r = x + y;

#define OP_INT_ADD_OVF(x,y,r,err) \
	r = x + y;              \
	if ((r^x) >= 0 || (r^y) >= 0); \
	else FAIL_OVF(err, "integer addition")

#define OP_INT_SUB(x,y,r,err)     r = x - y;

#define OP_INT_SUB_OVF(x,y,r,err) \
	r = x - y;              \
	if ((r^x) >= 0 || (r^~y) >= 0); \
	else FAIL_OVF(err, "integer subtraction")

#define OP_INT_MUL(x,y,r,err)     r = x * y;

#ifndef HAVE_LONG_LONG

#define OP_INT_MUL_OVF(x,y,r,err) \
	if (op_int_mul_ovf(x,y,&r)); \
	else FAIL_OVF(err, "integer multiplication")

#else

#define OP_INT_MUL_OVF(x,y,r,err) \
	{ \
		PY_LONG_LONG lr = (PY_LONG_LONG)x * (PY_LONG_LONG)y; \
		r = (long)lr; \
		if ((PY_LONG_LONG)r == lr); \
		else FAIL_OVF(err, "integer multiplication") \
	}
#endif

/* #define OP_ gnargll the division stuff is coming */

/* _________________ certain implementations __________________ */

#ifndef HAVE_LONG_LONG
/* adjusted from intobject.c, Python 2.3.3 */
int
op_int_mul_ovf(long a, long b, long *longprod)
{
	double doubled_longprod;	/* (double)longprod */
	double doubleprod;		/* (double)a * (double)b */

	*longprod = a * b;
	doubleprod = (double)a * (double)b;
	doubled_longprod = (double)*longprod;

	/* Fast path for normal case:  small multiplicands, and no info
	   is lost in either method. */
	if (doubled_longprod == doubleprod)
		return 1;

	/* Somebody somewhere lost info.  Close enough, or way off?  Note
	   that a != 0 and b != 0 (else doubled_longprod == doubleprod == 0).
	   The difference either is or isn't significant compared to the
	   true value (of which doubleprod is a good approximation).
	*/
	{
		const double diff = doubled_longprod - doubleprod;
		const double absdiff = diff >= 0.0 ? diff : -diff;
		const double absprod = doubleprod >= 0.0 ? doubleprod :
							  -doubleprod;
		/* absdiff/absprod <= 1/32 iff
		   32 * absdiff <= absprod -- 5 good bits is "close enough" */
		if (32.0 * absdiff <= absprod)
			return 1;
		return 0;
	}
}
#endif /* HAVE_LONG_LONG */
