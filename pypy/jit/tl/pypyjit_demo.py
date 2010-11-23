import cppyy

import time
import cppyy
lib = cppyy.load_lib("../../module/cppyy/test/example01Dict.so")
cls = cppyy._type_byname('example01')
inst = cls.construct(-17)

t1 = time.time()
res = 0
for i in range(10):
    res += inst.invoke("addDataToInt", i)
t2 = time.time()
print t2 - t1
