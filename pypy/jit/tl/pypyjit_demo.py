## base = object

## class Number(base):
##     __slots__ = ('val', )
##     def __init__(self, val=0):
##         self.val = val

##     def __add__(self, other):
##         if not isinstance(other, int):
##             other = other.val
##         return Number(val=self.val + other)
            
##     def __cmp__(self, other):
##         val = self.val
##         if not isinstance(other, int):
##             other = other.val
##         return cmp(val, other)

##     def __nonzero__(self):
##         return bool(self.val)

## def g(x, inc=2):
##     return x + inc

## def f(n, x, inc):
##     while x < n:
##         x = g(x, inc=1)
##     return x

## import time
## #t1 = time.time()
## #f(10000000, Number(), 1)
## #t2 = time.time()
## #print t2 - t1
## t1 = time.time()
## f(10000000, 0, 1)
## t2 = time.time()
## print t2 - t1

try:
##     from array import array

##     def coords(w,h):
##         y = 0
##         while y < h:
##             x = 0
##             while x < w:
##                 yield x,y
##                 x += 1
##             y += 1

##     def f(img):
##         sa=0
##         for x, y in coords(4,4):
##             sa += x * y
##         return sa

##     #img=array('h',(1,2,3,4))
##     print f(3)

    from array import array
    class Circular(array):
        def __new__(cls):
            self = array.__new__(cls, 'i', range(16))
            return self
        def __getitem__(self, i):
            #assert self.__len__() == 16 
            return array.__getitem__(self, i & 15)

    def main():
        buf = Circular()
        i = 10
        sa = 0
        while i < 20:
            #sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
            sa += buf[i]
            i += 1
        return sa

    import pypyjit
    pypyjit.set_param(threshold=3, inlining=True)
    print main()
    
except Exception, e:
    print "Exception: ", type(e)
    print e
    
## def f():
##     a=7
##     i=0
##     while i<4:
##         if  i<0: break
##         if  i<0: break
##         i+=1

## f()
