"""
To convert our IRM to an FRM machine, we must perform some swapping of the registers.  This is in effect
'paging', we are only allowed to perform XCHG operations on the slow (memory) registers, while we can do
anything with our fast (CPU registers).

There are various algorithms available, including the Linear Scan Algorithm (google this), but for now we
have decided to implement a simple, but (hopefully) reasonably effective last-recently-used algortithm.

Regardless of the swap algorithm , at each stage we must keep track of which IRM register is held in which
FRM register.  Our original test-suite simply gave the register usages, and checked the swap/usage sequence.

We need to rebuild the suite, checking the register map at EACH stage of the process.  Fiddly, but important!

We need some notation:

IRMxxx denotes an Infinite Register Machine that will use at most xxx registers

FRMxxx.yyy denotes a finite-register machine, with xxx fast registers, and a total of yyy registers.

"""


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

import sys

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
            #having swapped, if we have any stray mapping,remove it.

        else:
            val=goingin
        pipe=[val]+pipe
        re.append(val)

        if old2new.get(reg,reg)!=val:
            print regs
            print old2new
            print pipe
            print re
            sys.exit(1)
        if len(pipe)>n:
            popped=pipe.pop()   #this value fell out of the pipe

    print re
    return re


def remap(regs,n):
    pipe=[]
    old2new=range(len(regs)+1)
    re=[]
    for reg in regs:
        goingin=old2new[reg]
        #print reg,pipe,old2new
        if goingin>n:
            goingout=pipe[-1]
            re.append((goingin,goingout))

            old2new[goingout],old2new[goingin] = old2new[goingin],old2new[goingout]
            print '>>>',old2new
            #old2new[goingin]=goingout
            #old2new[goingout]=goingin

            val=goingout
            #having swapped, if we have any stray mapping,remove it.

        else:
            val=goingin
        pipe=[val]+pipe
        re.append(val)


        if len(pipe)>n:
            popped=pipe.pop()   #this value fell out of the pipe

    print re
    print range(20)
    print old2new
    return re


assert remap([1,2,3],3)==[1,2,3]
assert remap([1,2,3],2)==[1,2,(3,1),1]


assert remap([1,2,3,1],2)==[1,2,(3,1),1,(3,2),2]

assert remap([1,2,3,4,2],2)==[1,2,(3,1),1,(4,2),2,(4,1),1]
assert remap([1,2,3,2,1],2)==[1, 2, (3, 1), 1, 2, (3, 1), 1]

assert remap([1,2,3,4],1)==[1,(2,1),1,(3,1),1,(4,1),1]
assert remap([1,2,3,4,5,4,3,2,1],10)==[1,2,3,4,5,4,3,2,1]
assert remap([1,2,3,4,5,4,3,2,1],3)==[1,2,3,(4,1),1,(5,2),2,1,3,(5,2),2,(4,1),1]

#assert remap([1,2,4,3,4,1,5,3,5,6,1,2,8,7,6,8,9,7,9,10,1,2],5)==7   #this is a real-world example for PowerPC


class Machine:
    def __init__(self,nreg,regtot=100):
        self._nreg=nreg
        self._pipe=[]
        self._regtot=regtot
        self._old2new=range(0,regtot+1)  #this must be as big as the total number of registers+1 (we start at index 1)

    def regIRM(self,regIRM):
        ins=[]
        reg=regIRM
        goingin=self._old2new[reg]
        if goingin>self._nreg:
            goingout=self._pipe[-1]
            ins.append((goingin,goingout))
            self._old2new[goingout],self._old2new[goingin] = self._old2new[goingin],self._old2new[goingout]
            val=goingout
        else:
            val=goingin
        self._pipe=[val]+self._pipe
        ins.append(val)

        if len(self._pipe)>self._nreg:
            self._pipe.pop()   #this value fell out of the pipe

        self._lastFRMUSed=val
        return ins


    def lastFRMUsed(self):
        return self._lastFRMUsed

    def map(self):
        import operator
        """answer a map IRM notation -> current FRM notation"""
        map={}
        for reg in range(1,self._regtot+1):
            map[reg]=operator.indexOf(self._old2new,reg)
        return map

    def identityMap(self):
        """check that the current map is the identity map"""
        map=self.map()
        for reg in range(1,self._regtot+1):
            if map[reg]!=reg:
                return False
        return True

print '\n\n NEW SUITE \n\n'

machine=Machine(1,1)   #create an FRM1 using an IRM1 translation
assert machine.identityMap()  #check our registers
assert machine.regIRM(1)==[1]    # use IRM register 1,check emitted code is just usage of register 1
assert machine.map()=={1:1}

machine=Machine(1,2)  # FRM1 using IRM2 translation
assert machine.regIRM(1)==[1]         #use IRM1.1 ,no need to swap
assert machine.map()=={1:1,2:2}       #identity mapping is preserved.

assert machine.regIRM(2)==[(2,1),1]   #use IRM1.2.  We will need a swap
assert machine.map()=={1:2,2:1}       #now we have non-trival permutation.
assert not machine.identityMap()      #also, show it is not the identity map.(have to test this too!)

assert machine.regIRM(1)==[(2,1),1]   #use IRM1.1 again (this time we should get a swap)
assert machine.map()=={1:1,2:2}       #and recover the identity map

#now a more involved example

machine=Machine(3,5)  #2 real registers, from a machine which uses 5 registers
assert machine.identityMap()
assert machine.regIRM(1)==[1]
assert machine.regIRM(2)==[2]
assert machine.regIRM(3)==[3]
assert machine.regIRM(1)==[1]
assert machine.regIRM(4)==[(4,2),2]
assert machine.regIRM(2)==[(4,3),3]
assert machine.map()=={1:1,2:3,3:4,4:2,5:5}

machine=Machine(3,5)  #3 real registers, from a machine which uses 5 registers
assert machine.identityMap()
assert machine.regIRM(1)==[1]
assert machine.regIRM(2)==[2]
assert machine.regIRM(3)==[3]
assert machine.regIRM(4)==[(4,1),1]
assert machine.regIRM(5)==[(5,2),2]
assert machine.regIRM(2)==[(5,3),3]
assert machine.regIRM(3)==[2]


#assert machine.regIRM(2)==[(4,3),3]
#assert machine.map()=={1:1,2:3,3:4,4:2,5:5}













