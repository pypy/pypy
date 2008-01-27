"""
Awful code here.  Paste your example in "lines".  Change headers and
footers if necessary below.  The script tries to reduce it by removing
lines matching 'r' and changing lines matching 'rif' to 'if True' or 'if
False'.  The smallest failing example found so far gets written to
zsample.py.
"""
import autopath
import os
import re
r = re.compile(r"      \w = ")
rif = re.compile(r"      if \w:")

SEED = 73595
ITERATIONS = 10
ARGS=[-27, -38, -33, -53, 16, -28, 13, 11, 11, -46, -34, 57, -11, 80, 15, 49, -37, -43, -73, -62, -31, -21, -36, 17, 97, -53]
BACKEND = 'i386'


lines = """
    if goto == 0:
      u = n != e
      k = intmask(v + z)
      b = not f
      w = intmask(l % ((a & 0xfffff) + 1))
      h = a or y
      e = intmask(z + z)
      m = c != a
      a = intmask(v + g)
      n = intmask(c - x)
      n = intmask(o % ((y & 0xfffff) + 1))
      o = -7035
      h = m >= a
      s = f != g
      e = intmask(~w)
      if f:
        goto = 4
      else:
        goto = 3
    if goto == 1:
      n = intmask(h - c)
      x = t == b
      a = 7744
      if g:
        goto = 2
      else:
        goto = 2
    if goto == 2:
      i = intmask(i - v)
      o = -6878346
      f = intmask(i ^ n)
      i = 1261729270
      q = s or u
      z = t >= b
      u = bool(u)
      w = intmask(e << (c & 0x0000067f))
      if w:
        goto = 13
      else:
        goto = 14
    if goto == 3:
      y = intmask(w >> (e & 0x1234567f))
      d = intmask(o & j)
      r = r != n
      a = intmask(b & u)
      b = -11216
      v = intmask(g // (-((g & 0xfffff) + 2)))
      x = 6697939
      d = intmask(abs(q))
      i = intmask(i % (-((c & 0xfffff) + 2)))
      w = 23593
      u = n and a
      d = intmask(q << (y & 0x0000067f))
      o = intmask(w // (-((i & 0xfffff) + 2)))
      l = intmask(e + n)
      if j:
        counter -= 1
        if not counter: break
        goto = 2
      else:
        goto = 14
    if goto == 4:
      f = intmask(e * n)
      l = intmask(k >> (e & 0x1234567f))
      l = intmask(u // ((p & 0xfffff) + 1))
      d = bool(m)
      d = 7364461
      g = 1410833768
      g = y <= d
      s = l == d
      e = intmask(k - z)
      o = -6669177
      c = intmask(-o)
      q = intmask(-o)
      m = intmask(u - j)
      q = intmask(a - s)
      m = intmask(a | n)
      c = q and a
      t = intmask(b // (-((p & 0xfffff) + 2)))
      if r:
        goto = 5
      else:
        goto = 12
    if goto == 5:
      c = intmask(i * q)
      q = intmask(-q)
      c = intmask(a // (-((a & 0xfffff) + 2)))
      u = k >= i
      m = -34
      z = intmask(o - i)
      x = x and l
      w = o <  n
      x = n != w
      m = 92
      h = 27
      x = intmask(~u)
      i = not o
      q = intmask(c & q)
      y = x or g
      if z:
        goto = 10
      else:
        counter -= 1
        if not counter: break
        goto = 1
    if goto == 6:
      u = intmask(l // (-((g & 0xfffff) + 2)))
      m = intmask(l // ((h & 0xfffff) + 1))
      a = 3949664
      c = intmask(v - u)
      w = k and r
      q = -1898584839
      k = a >  o
      if d:
        goto = 7
      else:
        goto = 8
    if goto == 7:
      j = not f
      s = n == h
      t = x >  n
      z = intmask(e & f)
      q = intmask(v + k)
      o = not a
      v = 2876355
      h = intmask(w % ((p & 0xfffff) + 1))
      c = e and b
      k = intmask(f // (-((u & 0xfffff) + 2)))
      m = 4882866
      if h:
        counter -= 1
        if not counter: break
        goto = 0
      else:
        counter -= 1
        if not counter: break
        goto = 4
    if goto == 8:
      w = intmask(g & n)
      d = -31404
      s = intmask(abs(e))
      j = intmask(g << (w & 0x0000067f))
      r = -26
      b = -13356
      o = p <  m
      c = 438000325
      t = intmask(~g)
      i = intmask(-e)
      a = intmask(c - x)
      v = intmask(v >> (f & 0x1234567f))
      if o:
        counter -= 1
        if not counter: break
        goto = 6
      else:
        goto = 12
    if goto == 9:
      l = x <= h
      z = not w
      f = intmask(u ^ r)
      if m:
        counter -= 1
        if not counter: break
        goto = 7
      else:
        goto = 11
    if goto == 10:
      o = intmask(t // ((e & 0xfffff) + 1))
      w = c == v
      if h:
        counter -= 1
        if not counter: break
        goto = 5
      else:
        counter -= 1
        if not counter: break
        goto = 3
    if goto == 11:
      z = i != c
      t = d != w
      v = intmask(r - f)
      u = 6813995
      z = c <  f
      r = intmask(c + i)
      z = intmask(o - s)
      p = intmask(i // (-((n & 0xfffff) + 2)))
      v = intmask(p | h)
      if a:
        counter -= 1
        if not counter: break
        goto = 3
      else:
        counter -= 1
        if not counter: break
        goto = 0
    if goto == 12:
      b = intmask(l % ((a & 0xfffff) + 1))
      d = intmask(abs(y))
      c = intmask(~w)
      a = bool(v)
      d = not a
      v = intmask(s ^ u)
      if m:
        counter -= 1
        if not counter: break
        goto = 4
      else:
        counter -= 1
        if not counter: break
        goto = 8
    if goto == 13:
      c = 13780
      e = n != i
      x = 912031708
      i = intmask(p ^ j)
      k = not s
      p = c >  b
      o = intmask(~j)
      t = intmask(-k)
      v = y <= v
      v = m <= a
      w = a <  u
      z = p == v
      if g:
        counter -= 1
        if not counter: break
        goto = 7
      else:
        counter -= 1
        if not counter: break
        goto = 13
    if goto == 14:
      if p:
        counter -= 1
        if not counter: break
        goto = 8
      else:
        counter -= 1
        if not counter: break
        goto = 13
""".splitlines()

lines = [s.rstrip() for s in lines]
lines = [s for s in lines if s]


def accept(lines):
    g = open('zgen.py', 'w')
    print >> g, '''from pypy.rlib.rarithmetic import intmask

def dummyfn(counter, a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z):
  goto = 0
  while True:
    '''

    for line in lines:
        print >> g, line

    print >> g, '''
  return intmask(a*-468864544+b*-340864157+c*-212863774+d*-84863387+e*43136996+f*171137383+g*299137766+h*427138153+i*555138536+j*683138923+k*811139306+l*939139693+m*1067140076+n*1195140463+o*1323140846+p*1451141233+q*1579141616+r*1707142003+s*1835142386+t*1963142773+u*2091143156+v*-2075823753+w*-1947823370+x*-1819822983+y*-1691822600+z*-1563822213)

'''
    g.close()

    #ok = os.system("py.test zgen.py --seed=6661 -s") == 0

    from pypy.jit.codegen.demo import conftest as demo_conftest
    demo_conftest.option.randomseed = SEED
    demo_conftest.option.backend = BACKEND
    from pypy.jit.codegen.demo.support import rundemo

    d = {}
    execfile('zgen.py', d)
    dummyfn = d['dummyfn']

    childpid = os.fork()
    if childpid == 0:     # in child
        rundemo(dummyfn, ITERATIONS, *ARGS)
        os._exit(0)

    _, status = os.waitpid(childpid, 0)
    ok = status == 0

    if ok:
        return True     # accept
    else:
        os.system("cp -f zgen.py zsample.py")
        global progress
        progress = True
        globals()['lines'][:] = lines
        return False


assert not accept(lines)

progress = True
while progress:
    progress = False
    i = 0
    while i < len(lines):
        lines1 = lines[:]
        if r.match(lines[i]):
            del lines1[i]
            if not accept(lines1):
                continue
        elif rif.match(lines[i]):
            # try if 1: / if 0:
            lines1[i] = "      if True:"
            if not accept(lines1):
                continue
            lines1[i] = "      if False:"
            if not accept(lines1):
                continue
        i += 1

    print
    print
    print
    print
    print '\n'.join(lines)
    #import pdb; pdb.set_trace()
