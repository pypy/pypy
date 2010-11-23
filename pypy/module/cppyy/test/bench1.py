
import time
import cppyy
lib = cppyy.load_lib("./example01Dict.so")
cls = cppyy._type_byname("example01")
inst = cls.construct(0)

def g():
    res = 0
    for i in range(10000000):
        i

def f():
    res = 0
    for i in range(10000000):
        #inst.invoke("addDataToDouble", float(i))
        inst.invoke("addDataToInt", i)

g(); f();
t1 = time.time()
g()
t2 = time.time()
f()
t3 = time.time()
print t3 - t2, t2 - t1
print (t3 - t2) - (t2 - t1)
