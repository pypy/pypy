
try:
    class C:
        def __call__(self):
            pass

    def f():
        i = 0
        c = C()
        while i < 10:
            c()
            i += 1
    f()
except Exception, e:
    print "Exception: ", type(e)
    print e
    
