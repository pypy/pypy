# -*- coding: utf-8 -*-

import sys

def run(objs, n):
    res = 0
    for o in objs:
        for i in range(n):
            res += o.f()
    print res

def thefun():
    return 1

if __name__ == "__main__":
    try:
        num_types = int(sys.argv[1])
        n = int(sys.argv[2])
        objs = []
        for i in range(num_types):
            exec("""
class A_%s(object):
    field = %s
    #def f(self): return 1#return self.field
            """ % (i, i))
            objs.append(eval("A_%s()" % i))
            # use same 'thefun' for each obj (to avoid more failing guards)
            setattr(objs[-1], 'f', thefun)

        run(objs, n)
    except Exception as e:
        print e
        print "Arguments: num_types iterations"
        print "env PYPYLOG=jit-sum:- ./pypy-c --jit guard_value_limit=8 overspecialize_type.py  42 50000"
