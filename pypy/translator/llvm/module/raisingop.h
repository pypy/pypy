/* expanded macros of genc's c/int.h */

int pypyop_int_neg_ovf(int x) {
  long r = -x;
  if (x >= 0 || x != -x){
    return r;
  } else {
    raisePyExc_OverflowError("integer negate");
    return 0;
  }
}

int pypyop_int_abs_ovf(int x) {
  int r = x >= 0 ? x : -x;
  if (x >= 0 || x != -x) {
    return r;
  } else {
    raisePyExc_OverflowError("integer absolute");
    return 0;
  }
}

int pypyop_int_add_ovf(int x, int y) {
  int r = x + y;
  
  if ((r^x) >= 0 || (r^y) >= 0) {
    return r;
  } else {
    raisePyExc_OverflowError("integer addition");
    return 0;
  }
}

int pypyop_int_sub_ovf(int x, int y) {
  int r = x - y;
  
  if ((r^x) >= 0 || (r^(~y)) >= 0) {
    return r;
  } else {
    raisePyExc_OverflowError("integer subtraction");
    return 0;
  }

  return r;
}

int _pypyop_int_mul_ovf(long a, long b, long *longprod) {
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

int pypyop_int_mul_ovf(int x, int y) {
  long r;

#ifndef HAVE_LONG_LONG
  
  if (_pypyop_int_mul_ovf(x, y, &r)) {
      return r;
  } else {
    raisePyExc_OverflowError("integer multiplication");
  }

#else
  
  PY_LONG_LONG lr = (PY_LONG_LONG)(x) * (PY_LONG_LONG)(y);
  r = (long)lr;
  if ((PY_LONG_LONG)r == lr) {
    return r;
  } else {
    raisePyExc_OverflowError("integer multiplication");
  }
#endif
}

int pypyop_int_lshift_ovf_val(int x, int y) {
  int r;

  if (y < 0) {
    raisePyExc_ValueError("negative shift count");
    return 0;
  }

  r = x << y;
  if (x != Py_ARITHMETIC_RIGHT_SHIFT(long, r, y)) {
    raisePyExc_OverflowError("x<<y loosing bits or changing sign");
    return 0;
  }

  return r;
}

int pypyop_int_rshift_val(int x, int y) {
  if (y < 0) {
    raisePyExc_ValueError("negative shift count");
    return 0;
  } else {
    return x >> y;
  }
}

long _pypyop_divmod_adj(long x, long y, long *p_rem) {

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

int pypyop_int_floordiv_ovf_zer(int x, int y) {
  if (y) {
    if (y == -1 && x < 0 && ((unsigned long) x << 1) == 0) {
      raisePyExc_OverflowError("integer division");
      return 0;
      } else {
	return _pypyop_divmod_adj(x, y, NULL);
      }
  } else {
    raisePyExc_ZeroDivisionError("integer division");
    return 0;
  }
}

int pypyop_int_floordiv_zer(int x, int y) {
  if (y) {
    return _pypyop_divmod_adj(x, y, NULL);
  } else {
    raisePyExc_ZeroDivisionError("integer division");
    return 0;
  }
}

unsigned int pypyop_uint_floordiv_zer(unsigned int x, unsigned int y) {
  if (y) {
    return x / y;
  } else {
    raisePyExc_ZeroDivisionError("integer division");
    return 0;
  }
}

int pypyop_int_mod_ovf_zer(int x, int y) {
  long r;
  if (y) {
    if (y == -1 && x < 0 && ((unsigned long) x << 1) == 0) {
      _pypyop_divmod_adj(x, y, &r);
      return r;
    } else {
      raisePyExc_OverflowError("integer modulo");
      return 0;
    }

  } else {
    raisePyExc_ZeroDivisionError("integer modulo");
    return 0;
  }
}

int pypyop_int_mod_zer(int x, int y) {
  long r;
  if (y) {
      _pypyop_divmod_adj(x, y, &r);
      return r;
  } else {
    raisePyExc_ZeroDivisionError("integer modulo");
    return 0;
  }
}

unsigned int pypyop_uint_mod_zer(unsigned int x, unsigned int y) {
  unsigned long r;
  if (y) {
      _pypyop_divmod_adj(x, y, &r);
      return r;
  } else {
    raisePyExc_ZeroDivisionError("integer modulo");
    return 0;
  }
}
