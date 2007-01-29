"""
Awful code here.  Paste your example in "lines".  Change headers and
footers if necessary below.  The script tries to reduce it by removing
lines matching 'r' and changing lines matching 'rif' to 'if True' or 'if
False'.  The smallest failing example found so far gets written to
zsample.py.
"""
import os
import re
r = re.compile(r"      \w = ")
rif = re.compile(r"      if \w:")

lines = """
    if goto == 0:
      g = h and x
      a = intmask(d + g)
      goto = 13
    if goto == 1:
      if v:
        goto = 13
      else:
        goto = 9
    if goto == 2:
      if m:
        goto = 10
      else:
        goto = 3
    if goto == 3:
      if r:
        goto = 9
      else:
        counter -= 1
        if not counter: break
        goto = 0
    if goto == 4:
      if h:
        goto = 11
      else:
        goto = 9
    if goto == 5:
      x = intmask(-i)
      p = bool(h)
      b = m >  x
      g = p or i
      h = p >  v
      goto = 7
    if goto == 6:
      m = intmask(-p)
      counter -= 1
      if not counter: break
      goto = 5
    if goto == 7:
      if d:
        counter -= 1
        if not counter: break
        goto = 0
      else:
        goto = 0
    if goto == 8:
      if e:
        counter -= 1
        if not counter: break
        goto = 6
      else:
        counter -= 1
        if not counter: break
        goto = 6
    if goto == 9:
      if u:
        counter -= 1
        if not counter: break
        goto = 6
      else:
        counter -= 1
        if not counter: break
        goto = 2
    if goto == 10:
      if v:
        goto = 14
      else:
        goto = 12
    if goto == 11:
      if f:
        counter -= 1
        if not counter: break
        goto = 5
      else:
        counter -= 1
        if not counter: break
        goto = 11
    if goto == 12:
      d = d >= n
      counter -= 1
      if not counter: break
      goto = 0
    if goto == 13:
      l = j <= u
      d = intmask(s - y)
      h = intmask(l // ((h & 0xfffff) + 1))
      if a:
        counter -= 1
        if not counter: break
        goto = 12
      else:
        counter -= 1
        if not counter: break
        goto = 6
    if goto == 14:
      if o:
        counter -= 1
        if not counter: break
        goto = 14
      else:
        counter -= 1
        if not counter: break
        goto = 14
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

args=[-67, -89, -99, 35, 91, 8, -17, -75, 14, 88, 71, -77, -77, 38, 65, 21, 77, 73, -17, -12, -67, 36, 11, 25, -54, -36]


def test_y():
    from pypy.jit.codegen.demo.support import rundemo
    rundemo(dummyfn, 10, *args)
'''
    g.close()

    ok = os.system("py.test zgen.py --seed=3888 -s") == 0
    # XXX could run in-process to avoid start-up overhead

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
