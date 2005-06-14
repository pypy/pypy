
/************************************************************/
 /***  C header subsection: operations between ints        ***/

/*** unary operations ***/

#define OP_INT_IS_TRUE(x,r,err)   OP_INT_NE(x,0,r,err)

#define OP_INT_INVERT(x,r,err)    r = ~((long)(x));

#define OP_INT_POS(x,r,err)    r = x;

#define OP_INT_NEG(x,r,err)    r = -((long)x);

#define OP_INT_NEG_OVF(x,r,err) \
	OP_INT_NEG(x,r,err) \
	if ((long)(x) >= 0 || (long)(x) != -(long)(x)); \
	else FAIL_OVF(err, "integer negate")

#define OP_INT_ABS(x,r,err)    r = (long)(x) >= 0 ? x : -((long)x);

#define OP_INT_ABS_OVF(x,r,err) \
	OP_INT_ABS(x,r,err) \
	if ((long)(x) >= 0 || (long)(x) != -(long)(x)); \
	else FAIL_OVF(err, "integer absolute")

/***  binary operations ***/

#define OP_INT_EQ(x,y,r,err)	  r = ((long)(x) == (long)(y));
#define OP_INT_NE(x,y,r,err)	  r = ((long)(x) != (long)(y));
#define OP_INT_LE(x,y,r,err)	  r = ((long)(x) <= (long)(y));
#define OP_INT_GT(x,y,r,err)	  r = ((long)(x) >  (long)(y));
#define OP_INT_LT(x,y,r,err)	  r = ((long)(x) <  (long)(y));
#define OP_INT_GE(x,y,r,err)	  r = ((long)(x) >= (long)(y));

#define OP_INT_CMP(x,y,r,err) \
	r = (((long)(x) > (long)(y)) - ((long)(x) < (long)(y)))

/* addition, subtraction */

#define OP_INT_ADD(x,y,r,err)     r = (long)(x) + (long)(y);

#define OP_INT_ADD_OVF(x,y,r,err) \
	OP_INT_ADD(x,y,r,err) \
	if ((r^((long)x)) >= 0 || (r^((long)y)) >= 0); \
	else FAIL_OVF(err, "integer addition")

#define OP_INT_SUB(x,y,r,err)     r = (long)(x) - (long)(y);

#define OP_INT_SUB_OVF(x,y,r,err) \
	OP_INT_SUB(x,y,r,err) \
	if ((r^(long)(x)) >= 0 || (r^~(long)(y)) >= 0); \
	else FAIL_OVF(err, "integer subtraction")

#define OP_INT_MUL(x,y,r,err)     r = (long)(x) * (long)(y);

#ifndef HAVE_LONG_LONG

#define OP_INT_MUL_OVF(x,y,r,err) \
	if (op_int_mul_ovf(x,y,&r)); \
	else FAIL_OVF(err, "integer multiplication")

#else

#define OP_INT_MUL_OVF(x,y,r,err) \
	{ \
		PY_LONG_LONG lr = (PY_LONG_LONG)(x) * (PY_LONG_LONG)(y); \
		r = (long)lr; \
		if ((PY_LONG_LONG)r == lr); \
		else FAIL_OVF(err, "integer multiplication") \
	}
#endif

/* shifting */

#define OP_INT_RSHIFT(x,y,r,err) \
	if ((long)(y) < LONG_BIT) \
		r = Py_ARITHMETIC_RIGHT_SHIFT(long, (long)(x), (long)(y)); \
	else r = (long)(x) < 0 ? -1 : 0;

#define OP_INT_RSHIFT_VAL(x,y,r,err) \
	if ((long)(y) >= 0) { OP_INT_RSHIFT(x,y,r,err) } \
	else FAIL_VAL(err, "negative shift count")

#define OP_INT_LSHIFT(x,y,r,err) \
	if ((long)(y) < LONG_BIT) \
		r = (long)(x) << (long)(y); \
	else r = 0;

#define OP_INT_LSHIFT_VAL(x,y,r,err) \
	if ((long)(y) >= 0) { OP_INT_LSHIFT(x,y,r,err) } \
	else FAIL_VAL(err, "negative shift count")

#define OP_INT_LSHIFT_OVF(x,y,r,err) \
	OP_INT_LSHIFT(x,y,r,err) \
	if ((long)(x) != Py_ARITHMETIC_RIGHT_SHIFT(long, r, (long)(y))) \
		FAIL_OVF(err, "x<<y loosing bits or changing sign")

#define OP_INT_LSHIFT_OVF_VAL(x,y,r,err) \
	if ((long)(y) >= 0) { OP_INT_LSHIFT_OVF(x,y,r,err) } \
	else FAIL_VAL(err, "negative shift count")


/* floor division */

#define OP_INT_FLOORDIV(x,y,r,err) r = op_divmod_adj(x, y, NULL);

#define OP_INT_FLOORDIV_OVF(x,y,r,err) \
	if ((long)(y) == -1 && (long)(x) < 0 && (long)(x) == -(long)(x)) \
		FAIL_OVF(err, "integer division") \
	OP_INT_FLOORDIV(x,y,r,err)

#define OP_INT_FLOORDIV_ZER(x,y,r,err) \
	if ((long)(y)) { OP_INT_FLOORDIV(x,y,r,err) } \
	else FAIL_ZER(err, "integer division")
		
#define OP_INT_FLOORDIV_OVF_ZER(x,y,r,err) \
	if ((long)(y)) { OP_INT_FLOORDIV_OVF(x,y,r,err) } \
	else FAIL_ZER(err, "integer division")

/* modulus */

#define OP_INT_MOD(x,y,r,err)     op_divmod_adj(x, y, &r);

#define OP_INT_MOD_OVF(x,y,r,err) \
	if ((long)(y) == -1 && (long)(x) < 0 && (long)x == -(long)(x)) \
		FAIL_OVF(err, "integer modulo") \
	OP_INT_MOD(x,y,r,err);

#define OP_INT_MOD_ZER(x,y,r,err) \
	if ((long)(y)) { OP_INT_MOD(x,y,r,err) } \
	else FAIL_ZER(err, "integer modulo")
		
#define OP_INT_MOD_OVF_ZER(x,y,r,err) \
	if ((long)(y)) { OP_INT_MOD_OVF(x,y,r,err) } \
	else FAIL_ZER(err, "integer modulo")

/*** conversions ***/

#define OP_CAST_BOOL_TO_INT(x,r,err)    r = (long)(x);
#define OP_CAST_BOOL_TO_UINT(x,r,err)   r = (unsigned long)(x);
#define OP_CAST_UINT_TO_INT(x,r,err)    r = (long)(x);
#define OP_CAST_INT_TO_UINT(x,r,err)    r = (unsigned long)(x);
#define OP_CAST_CHAR_TO_INT(x,r,err)    r = (long)(x);
#define OP_CAST_INT_TO_CHAR(x,r,err)    r = (char)(x);

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

/* XXX we might probe the compiler whether it does what we want */

long op_divmod_adj(long x, long y, long *p_rem)
{
	long xdivy = x / y;
	long xmody = x - xdivy * y;
	/* If the signs of x and y differ, and the remainder is non-0,
	 * C89 doesn't define whether xdivy is now the floor or the
	 * ceiling of the infinitely precise quotient.  We want the floor,
	 * and we have it iff the remainder's sign matches y's.
	 */
	if (xmody && ((y ^ xmody) < 0) /* i.e. and signs differ */) {
		xmody += y;
		--xdivy;
		assert(xmody && ((y ^ xmody) >= 0));
	}
	if (p_rem)
		*p_rem = xmody;
	return xdivy;
}
