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
    return None

def sum(L, a):
    print "sum", a
    Head, Tail = newvar(), newvar()
    unify(L, (Head, Tail))
    if Tail != None:
        return sum(Tail, Head + a)
    return a + Head

print "eager producer consummer"
print "before"
X = newvar()
S = newvar()
bind(S, uthread(sum, X, 0))
unify(X, uthread(generate, 0, 10))
print "after"

assert S == 45
print S # needs a special treatment
