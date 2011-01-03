
try:
    import pypyjit
    pypyjit.set_param(threshold=3, inlining=True)

    def main():
        i=a=0
        while i<10:
            i+=1
            a+=1
        return a

    print main()
    
except Exception, e:
    print "Exception: ", type(e)
    print e
    
