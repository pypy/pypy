
/************************************************************/
 /***  C header subsection: operations between ints        ***/


/*** unary operations ***/

#define OP_INT_IS_TRUE(x,r)   r = ((x) != 0)
#define OP_INT_INVERT(x,r)    r = ~(x)
#define OP_INT_NEG(x,r)       r = -(x)

#define OP_INT_NEG_OVF(x,r) \
	if ((x) == LONG_MIN) FAIL_OVF("integer negate"); \
	OP_INT_NEG(x,r)

#define OP_INT_ABS(x,r)    r = (x) >= 0 ? x : -(x)

#define OP_INT_ABS_OVF(x,r) \
	if ((x) == LONG_MIN) FAIL_OVF("integer absolute"); \
	OP_INT_ABS(x,r)

/***  binary operations ***/

#define OP_INT_EQ(x,y,r)	  r = ((x) == (y))
#define OP_INT_NE(x,y,r)	  r = ((x) != (y))
#define OP_INT_LE(x,y,r)	  r = ((x) <= (y))
#define OP_INT_GT(x,y,r)	  r = ((x) >  (y))
#define OP_INT_LT(x,y,r)	  r = ((x) <  (y))
#define OP_INT_GE(x,y,r)	  r = ((x) >= (y))

/* Implement INT_BETWEEN by optimizing for the common case where a and c
   are constants (the 2nd subtraction below is then constant-folded), or
   for the case of a == 0 (both subtractions are then constant-folded).
   Note that the following line only works if a <= c in the first place,
   which we assume is true. */
#define OP_INT_BETWEEN(a,b,c,r)   r = (((unsigned long)b - (unsigned long)a) \
                                     < ((unsigned long)c - (unsigned long)a))

/* addition, subtraction */

#define OP_INT_ADD(x,y,r)     r = (x) + (y)

/* cast to avoid undefined behaviour on overflow */
#define OP_INT_ADD_OVF(x,y,r) \
        r = (long)((unsigned long)x + y); \
        if ((r^x) < 0 && (r^y) < 0) FAIL_OVF("integer addition")

#define OP_INT_ADD_NONNEG_OVF(x,y,r)  /* y can be assumed >= 0 */ \
        r = (long)((unsigned long)x + y); \
        if ((r&~x) < 0) FAIL_OVF("integer addition")

#define OP_INT_SUB(x,y,r)     r = (x) - (y)

#define OP_INT_SUB_OVF(x,y,r) \
        r = (long)((unsigned long)x - y); \
        if ((r^x) < 0 && (r^~y) < 0) FAIL_OVF("integer subtraction")

#define OP_INT_MUL(x,y,r)     r = (x) * (y)

#if SIZEOF_LONG * 2 <= SIZEOF_LONG_LONG
#define OP_INT_MUL_OVF(x,y,r) \
	{ \
		long long _lr = (long long)x * y; \
		r = (long)_lr; \
		if (_lr != (long long)r) FAIL_OVF("integer multiplication"); \
	}
#else
#define OP_INT_MUL_OVF(x,y,r) \
	r = op_llong_mul_ovf(x, y)   /* long == long long */
#endif

/* shifting */

/* NB. shifting has same limitations as C: the shift count must be
       >= 0 and < LONG_BITS. */
#define CHECK_SHIFT_RANGE(y, bits) RPyAssert(y >= 0 && y < bits, \
	       "The shift count is outside of the supported range")


#define OP_INT_RSHIFT(x,y,r)    CHECK_SHIFT_RANGE(y, PYPY_LONG_BIT); \
						r = Py_ARITHMETIC_RIGHT_SHIFT(long, x, (y))
#define OP_UINT_RSHIFT(x,y,r)   CHECK_SHIFT_RANGE(y, PYPY_LONG_BIT); \
						r = (x) >> (y)
#define OP_LLONG_RSHIFT(x,y,r)  CHECK_SHIFT_RANGE(y, PYPY_LONGLONG_BIT); \
						r = Py_ARITHMETIC_RIGHT_SHIFT(PY_LONG_LONG,x, (y))
#define OP_ULLONG_RSHIFT(x,y,r) CHECK_SHIFT_RANGE(y, PYPY_LONGLONG_BIT); \
						r = (x) >> (y)


#define OP_INT_LSHIFT(x,y,r)    CHECK_SHIFT_RANGE(y, PYPY_LONG_BIT); \
							r = (x) << (y)
#define OP_UINT_LSHIFT(x,y,r)   CHECK_SHIFT_RANGE(y, PYPY_LONG_BIT); \
							r = (x) << (y)
#define OP_LLONG_LSHIFT(x,y,r)  CHECK_SHIFT_RANGE(y, PYPY_LONGLONG_BIT); \
							r = (x) << (y)
#define OP_ULLONG_LSHIFT(x,y,r) CHECK_SHIFT_RANGE(y, PYPY_LONGLONG_BIT); \
							r = (x) << (y)

#define OP_INT_LSHIFT_OVF(x,y,r) \
	OP_INT_LSHIFT(x,y,r); \
	if ((x) != Py_ARITHMETIC_RIGHT_SHIFT(long, r, (y))) \
		FAIL_OVF("x<<y losing bits or changing sign")

/* floor division */

#define OP_INT_FLOORDIV(x,y,r)    r = (x) / (y)
#define OP_UINT_FLOORDIV(x,y,r)   r = (x) / (y)
#define OP_LLONG_FLOORDIV(x,y,r)  r = (x) / (y)
#define OP_ULLONG_FLOORDIV(x,y,r) r = (x) / (y)

#define OP_INT_FLOORDIV_OVF(x,y,r)                      \
	if ((y) == -1 && (x) == LONG_MIN)               \
	    { FAIL_OVF("integer division"); r=0; }      \
	else                                            \
	    r = (x) / (y)

#define OP_INT_FLOORDIV_ZER(x,y,r)                      \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer division"); r=0; }      \
	else                                            \
	    r = (x) / (y)
#define OP_UINT_FLOORDIV_ZER(x,y,r)                             \
	if ((y) == 0)                                           \
	    { FAIL_ZER("unsigned integer division"); r=0; }     \
	else                                                    \
	    r = (x) / (y)
#define OP_LLONG_FLOORDIV_ZER(x,y,r)                    \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer division"); r=0; }      \
	else                                            \
	    r = (x) / (y)
#define OP_ULLONG_FLOORDIV_ZER(x,y,r)                           \
	if ((y) == 0)                                           \
	    { FAIL_ZER("unsigned integer division"); r=0; }     \
	else                                                    \
	    r = (x) / (y)

#define OP_INT_FLOORDIV_OVF_ZER(x,y,r)                  \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer division"); r=0; }      \
	else                                            \
	    { OP_INT_FLOORDIV_OVF(x,y,r); }

/* modulus */

#define OP_INT_MOD(x,y,r)     r = (x) % (y)
#define OP_UINT_MOD(x,y,r)    r = (x) % (y)
#define OP_LLONG_MOD(x,y,r)   r = (x) % (y)
#define OP_ULLONG_MOD(x,y,r)  r = (x) % (y)

#define OP_INT_MOD_OVF(x,y,r)                           \
	if ((y) == -1 && (x) == LONG_MIN)               \
	    { FAIL_OVF("integer modulo"); r=0; }        \
	else                                            \
	    r = (x) % (y)
#define OP_INT_MOD_ZER(x,y,r)                           \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer modulo"); r=0; }        \
	else                                            \
	    r = (x) % (y)
#define OP_UINT_MOD_ZER(x,y,r)                                  \
	if ((y) == 0)                                           \
	    { FAIL_ZER("unsigned integer modulo"); r=0; }       \
	else                                                    \
	    r = (x) % (y)
#define OP_LLONG_MOD_ZER(x,y,r)                         \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer modulo"); r=0; }        \
	else                                            \
	    r = (x) % (y)
#define OP_ULLONG_MOD_ZER(x,y,r)                                \
	if ((y) == 0)                                           \
	    { FAIL_ZER("unsigned integer modulo"); r=0; }       \
	else                                                    \
	    r = (x) % (y)

#define OP_INT_MOD_OVF_ZER(x,y,r)                       \
	if ((y) == 0)                                   \
	    { FAIL_ZER("integer modulo"); r=0; }        \
	else                                            \
	    { OP_INT_MOD_OVF(x,y,r); }

/* bit operations */

#define OP_INT_AND(x,y,r)     r = (x) & (y)
#define OP_INT_OR( x,y,r)     r = (x) | (y)
#define OP_INT_XOR(x,y,r)     r = (x) ^ (y)

/*** conversions ***/

#define OP_CAST_BOOL_TO_INT(x,r)    r = (long)(x)
#define OP_CAST_BOOL_TO_UINT(x,r)   r = (unsigned long)(x)
#define OP_CAST_UINT_TO_INT(x,r)    r = (long)(x)
#define OP_CAST_INT_TO_UINT(x,r)    r = (unsigned long)(x)
#define OP_CAST_INT_TO_LONGLONG(x,r) r = (long long)(x)
#define OP_CAST_CHAR_TO_INT(x,r)    r = (long)((unsigned char)(x))
#define OP_CAST_INT_TO_CHAR(x,r)    r = (char)(x)
#define OP_CAST_PTR_TO_INT(x,r)     r = (long)(x)    /* XXX */

#define OP_TRUNCATE_LONGLONG_TO_INT(x,r) r = (long)(x)

#define OP_CAST_UNICHAR_TO_INT(x,r)    r = (long)((unsigned long)(x)) /*?*/
#define OP_CAST_INT_TO_UNICHAR(x,r)    r = (unsigned int)(x)

/* bool operations */

#define OP_BOOL_NOT(x, r) r = !(x)

/* _________________ certain implementations __________________ */

/* adjusted from intobject.c, Python 2.3.3 */

/* prototypes */

long long op_llong_mul_ovf(long long a, long long b);

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

long long op_llong_mul_ovf(long long a, long long b)
{
	double doubled_longprod;	/* (double)longprod */
	double doubleprod;		/* (double)a * (double)b */
	long long longprod;

	longprod = a * b;
	doubleprod = (double)a * (double)b;
	doubled_longprod = (double)longprod;

	/* Fast path for normal case:  small multiplicands, and no info
	   is lost in either method. */
	if (doubled_longprod == doubleprod)
		return longprod;

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
			return longprod;

		FAIL_OVF("integer multiplication");
		return -1;
	}
}

#endif /* PYPY_NOT_MAIN_FILE */

/* implementations */

#define OP_UINT_IS_TRUE OP_INT_IS_TRUE
#define OP_UINT_INVERT OP_INT_INVERT
#define OP_UINT_ADD OP_INT_ADD
#define OP_UINT_SUB OP_INT_SUB
#define OP_UINT_MUL OP_INT_MUL
#define OP_UINT_LT OP_INT_LT
#define OP_UINT_LE OP_INT_LE
#define OP_UINT_EQ OP_INT_EQ
#define OP_UINT_NE OP_INT_NE
#define OP_UINT_GT OP_INT_GT
#define OP_UINT_GE OP_INT_GE
#define OP_UINT_AND OP_INT_AND
#define OP_UINT_OR OP_INT_OR
#define OP_UINT_XOR OP_INT_XOR

#define OP_LLONG_IS_TRUE OP_INT_IS_TRUE
#define OP_LLONG_NEG     OP_INT_NEG
#define OP_LLONG_ABS     OP_INT_ABS
#define OP_LLONG_INVERT  OP_INT_INVERT

#define OP_LLONG_ADD OP_INT_ADD
#define OP_LLONG_SUB OP_INT_SUB
#define OP_LLONG_MUL OP_INT_MUL
#define OP_LLONG_LT  OP_INT_LT
#define OP_LLONG_LE  OP_INT_LE
#define OP_LLONG_EQ  OP_INT_EQ
#define OP_LLONG_NE  OP_INT_NE
#define OP_LLONG_GT  OP_INT_GT
#define OP_LLONG_GE  OP_INT_GE
#define OP_LLONG_AND    OP_INT_AND
#define OP_LLONG_OR     OP_INT_OR
#define OP_LLONG_XOR    OP_INT_XOR

#define OP_ULLONG_IS_TRUE OP_LLONG_IS_TRUE
#define OP_ULLONG_INVERT  OP_LLONG_INVERT
#define OP_ULLONG_ADD OP_LLONG_ADD
#define OP_ULLONG_SUB OP_LLONG_SUB
#define OP_ULLONG_MUL OP_LLONG_MUL
#define OP_ULLONG_LT OP_LLONG_LT
#define OP_ULLONG_LE OP_LLONG_LE
#define OP_ULLONG_EQ OP_LLONG_EQ
#define OP_ULLONG_NE OP_LLONG_NE
#define OP_ULLONG_GT OP_LLONG_GT
#define OP_ULLONG_GE OP_LLONG_GE
#define OP_ULLONG_AND OP_LLONG_AND
#define OP_ULLONG_OR OP_LLONG_OR
#define OP_ULLONG_XOR OP_LLONG_XOR
