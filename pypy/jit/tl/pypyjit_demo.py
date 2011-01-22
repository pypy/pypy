
try:
    import pypyjit
    pypyjit.set_param(threshold=3, inlining=True)

    def sqrt(y, n=10000):
        x = y / 2
        while n > 0:
            #assert y > 0 and x > 0
            if y > 0 and x > 0: pass
            n -= 1
            x = (x + y/x) / 2
        return x

    print sqrt(1234, 4)
    
except Exception, e:
    print "Exception: ", type(e)
    print e
    
