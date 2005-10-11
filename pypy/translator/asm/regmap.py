

import random
random.seed(101)
n=10
m=5
initial=[ random.randint(1,m) for x in range(n)]

#now recode to n-register machine

def remap(regs,n):
    return regs

def remap(regs,n):
    pipe=[]
    old2new={}
    re=[]
    for reg in regs:
        goingin=old2new.get(reg,reg)

        if goingin>n:
            goingout=pipe[-1]
            re.append((goingin,goingout))
            old2new[goingin]=goingout
            old2new[goingout]=goingin
            reg=goingout
            pipe=[goingin]+pipe
            val2append=goingout
        else:
            val2append=goingin
            if val2append not in pipe:
                pipe=[val2append]+pipe
        if len(pipe)>n:
            pipe.pop()
        re.append(val2append)
    print re
    return re


def remap(regs,n):
    pipe=[]
    old2new={}
    re=[]
    for reg in regs:
        goingin=old2new.get(reg,reg)
        #print reg,pipe,old2new
        if goingin>n:
            goingout=pipe[-1]
            re.append((goingin,goingout))
            old2new[goingin]=goingout
            old2new[goingout]=goingin
            val=goingout
        else:
            val=goingin
        pipe=[val]+pipe
        re.append(val)
        if len(pipe)>n:
            pipe.pop()
    return re


assert remap([1,2,3],3)==[1,2,3]
assert remap([1,2,3],2)==[1,2,(3,1),1]
assert remap([1,2,3,1],2)==[1,2,(3,1),1,(3,2),2]
assert remap([1,2,3,4,2],2)==[1,2,(3,1),1,(4,2),2,(4,1),1]
assert remap([1,2,3,2,1],2)==[1, 2, (3, 1), 1, 2, (3, 1), 1]

assert remap([1,2,3,4],1)==[1,(2,1),1,(3,1),1,(4,1),1]
assert remap([1,2,3,4,5,4,3,2,1],10)==[1,2,3,4,5,4,3,2,1]
assert remap([1,2,3,4,5,4,3,2,1],3)==[1,2,3,(4,1),1,(5,2),2,1,3,(5,2),2,(4,1),1]





