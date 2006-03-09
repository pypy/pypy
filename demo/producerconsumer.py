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

print "before"
X = newvar()
S = newvar()
S == uthread(sum, X, 0)
X == uthread(generate, 0, 10)
print "after"

print S
