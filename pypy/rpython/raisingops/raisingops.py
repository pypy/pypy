from pypy.rpython.rarithmetic import r_longlong

def _pypyop_divmod_adj(x, y, p_rem=None):
  xdivy = r_longlong(x / y)
  xmody = r_longlong(x - xdivy * y)
  
  # If the signs of x and y differ, and the remainder is non-0,
  # C89 doesn't define whether xdivy is now the floor or the
  # ceiling of the infinitely precise quotient.  We want the floor,
  # and we have it iff the remainder's sign matches y's.
  if xmody and ((y ^ xmody) < 0):
  
    xmody += y
    xdivy -= 1
    assert xmody and ((y ^ xmody) >= 0)

  #XXX was a pointer
  # if p_rem
  #  p_rem = xmody;
  return xdivy

def int_floordiv_zer(x,y):
  if y:
    return _pypyop_divmod_adj(x, y)
  else:
    raise ZeroDivisionError("integer division")
