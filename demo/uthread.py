"""This is an example that uses the (prototype) Logic Object Space. To run,
you have to set USE_GREENLETS in pypy.objspace.logic to True and do:
  
    $ py.py -o logic uthread.py

newvar creates a new unbound logical variable. If you try to access an unbound
variable, the current uthread is blocked, until the variable is bound.
"""

X = newvar()
Y = newvar()

bind(Y, X) # aliasing

def f():
    print "starting"
    print is_free(X)
    if Y:
        print "ok"
        return
    print "false"
    return

def bind():
    unify(X, 1)

uthread(f)
print "afterwards"
uthread(bind)
