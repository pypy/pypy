import py
from pypy.rlib.rarithmetic import intmask
from pypy.jit.codegen.i386.demo.support import rundemo, Random

# try running this with the following py.test options:
#
#   --view       shows the input llgraph and the output machine code
#
#   --seed=N     force a given random seed, for reproducible results.
#                if not given, multiple runs build the machine code
#                in different order, explicitly to stress the backend
#                in different ways.
#
#   --benchmark  benchmark the result code


def test_factorial():
    def fact(n):
        result = 1
        while n > 1:
            result *= n
            n -= 1
        return result
    rundemo(fact, 10)

def test_pseudofactorial():
    def pseudofact(n):
        result = 1
        while n > 1:
            if n & 1:
                result *= n
            n -= 1
        return result
    rundemo(pseudofact, 10)

def test_f1():
    def f1(n):
        "Arbitrary test function."
        i = 0
        x = 1
        while i<n:
            j = 0
            while j<=i:
                j = j + 1
                x = x + (i&j)
            i = i + 1
        return x
    #rundemo(f1, 2117)
    rundemo(f1, 217)

def test_random_function():
    py.test.skip("in-progress (e.g. --seed=225 shows a backend crash)")
    from pypy.rlib.unroll import SpecTag
    blocklabels = range(15)
    r = Random()
    vars = list("abcdefghijklmnopqrstuvwxyz")
    varlist = ', '.join(vars)
    magicsum = '+'.join(['%s^%d' % (v, hash(v)) for v in vars])
    operations = ['%s + %s',
                  '%s + %s',
                  '%s - %s',
                  '%s - %s',
                  '%s * %s',
                  '%s & %s',
                  '%s | %s',
                  '%s ^ %s',
                  '%s << abs(%s)',
                  '%s >> abs(%s)',
                  'abs(%s)',
                  '-%s',
                  '~%s',
                  '%s // ((%s & 0xfffff) + 1)',
                  '%s // (-((%s & 0xfffff) + 1))',
                  '%s %% ((%s & 0xfffff) + 1)',
                  '%s %% (-((%s & 0xfffff) + 1))',
                  '!%s or %s',
                  '!%s and %s',
                  '!not %s',
                  '!bool(%s)',
                  '!%s <  %s',
                  '!%s <= %s',
                  '!%s == %s',
                  '!%s != %s',
                  '!%s >  %s',
                  '!%s >= %s',
                  ]
    lines = ["def dummyfn(%(varlist)s):" % locals(),
             "  goto = blocktag0",
             "  counter = 10000",
             "  while counter > 0:",
             "    counter -= 1"]
    for i in blocklabels:
        lines.append("    if goto is blocktag%d:" % i)
        for j in range(r.randrange(0, 20)):
            v1 = r.choice(vars)
            constbytes = r.randrange(-15, 5)
            if constbytes <= 0:
                v2 = r.choice(vars)
                op = r.choice(operations)
                if op.count('%s') == 1:
                    op = op % (v2,)
                else:
                    v3 = r.choice(vars)
                    op = op % (v2, v3)
                if op.startswith('!'):
                    op = op[1:]
                else:
                    op = 'intmask(%s)' % op
                lines.append("      %s = %s" % (v1, op))
            else:
                constant = r.randrange(-128, 128)
                for i in range(1, constbytes):
                    constant = constant << 8 | r.randrange(0, 256)
                lines.append("      %s = %d" % (v1, constant))
        v1 = r.choice(vars)
        lines.append("      if %s: goto = blocktag%d" %
                     (v1, r.choice(blocklabels)))
        lines.append("      else: goto = blocktag%d" %
                     (r.choice(blocklabels),))
    lines.append("  del goto")
    lines.append("  return intmask(%(magicsum)s)" % locals())

    miniglobals = {'intmask': intmask}
    for i in blocklabels:
        miniglobals['blocktag%d' % i] = SpecTag()
    src = py.code.Source('\n'.join(lines))
    exec src.compile() in miniglobals
    dummyfn = miniglobals['dummyfn']

    args = [r.randrange(-99, 100) for v1 in vars]
    rundemo(dummyfn, *args)
