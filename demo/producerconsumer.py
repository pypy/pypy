"""This is an example that uses the (prototype) Logic Object Space. To run,
you have to set USE_GREENLETS in pypy.objspace.logic to True and do:
  
    $ py.py -o logic producerconsumer.py

newvar creates a new unbound logical variable. If you try to access an unbound
variable, the current uthread is blocked, until the variable is bound.
"""

def generate(n, limit):
    print "generate", n, limit
    if n < limit:
        return (n, generate(n + 1, limit))
    return (None, None)

def sum(L, a):
    print "sum", a
    head, Tail = newvar(), newvar()
    L == (head, Tail)
    if head != None:
        return sum(Tail, head + a)
    return a

print "eager producer consummer"
print "before"
X = newvar()
S = newvar()
S == uthread(sum, X, 0)
X == uthread(generate, 0, 10)
print "after"

print S


def lgenerate(n, L):
    """wait-needed version of generate"""
    print "generator waits on L being needed"
    wait_needed(L)
    Tail = newvar()
    L == (n, Tail)
    print "generator bound L to", L
    lgenerate(n+1, Tail)

def lsum(L, a, limit):
    """this version of sum controls the generator"""
    print "sum", a
    if limit > 0:
        Head, Tail = newvar(), newvar()
        print "sum waiting on L"
        Head, Tail = L # or L = (Head, Tail) ... ?
        return lsum(Tail, a+Head, limit-1)
    else:
        return a

print "lazy producer consummer"
print "before"
Y = newvar()
T = newvar()
uthread(lgenerate, 0, Y)
T == uthread(lsum, Y, 0, 10)
print "after"

print T
