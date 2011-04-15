
try:
    class A(object):
        def meth(self):
            for k in range(4):
                pass

    def f():
        a = A()
        for i in range(20):
            a.meth()

    f()

except Exception, e:
    print "Exception: ", type(e)
    print e
    
