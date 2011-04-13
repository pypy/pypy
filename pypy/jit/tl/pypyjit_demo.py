
try:
    def main(n):
        def g(n):
            return range(n)
        s = 0
        for i in range(n):  # ID: for
            tmp = g(n)
            s += tmp[i]     # ID: getitem
            a = 0
        return s
    main(10)

except Exception, e:
    print "Exception: ", type(e)
    print e
    
