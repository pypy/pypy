""" IRM Simulator """
import autopath
from pypy.rpython.llinterp import LLFrame
from pypy.translator.asm.infregmachine import Instruction
from pypy.objspace.flow.model import Constant

"""
Notes on the register allocation algorithm:


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


def regmap(regperm):
    import operator
    """answer a map IRM notation -> current FRM notation"""
    map={}
    for reg in range(1,len(regperm)):
        #print reg,map,regperm
        map[reg]=regperm.index(reg)
    return map

def maxRegister(commands):
    pool=[]
    for cmd in commands:
        if not isinstance(cmd,str):
            pool+=cmd.registers_used()
    if pool==[]:
        return 1
    return max(pool)


def TranslateProgram(commands,nreg):
    """answer this program into one which only uses nreg fast registers"""
    totreg=maxRegister(commands)
    assert nreg>=3 ,'Some commands may use 3 registers!!!!'
    newprog=[]
    pipe=[]
    old2new=range(0,totreg+1)  #this must be as big as the total number of registers+1 (we start at index 1)


    for cmd in commands:
        #if we use any registers, we must possibly swap first, and then remap
        if  isinstance(cmd,str) or cmd.name in ('J','JT','JF'): #label or jump so  pass through
            newprog.append(cmd)
        else:
            #so now remap the registers!

            regused=cmd.registers_used()
            t2p=[old2new[x] for x in regused]
            for reg in regused:
                goingin=regmap(old2new)[reg]
                if goingin>nreg:
                    if pipe[-1] not in t2p:
                        index=-1
                    elif pipe[-2] not in t2p:
                        index=-2
                    else:
                        assert pipe[-3]!=goingin #this must be true for nreg>=3
                        index=-3
                    #now swap to end of pipe, so code as before works.
                    pipe[index],pipe[-1]=pipe[-1],pipe[index]
                    goingout=pipe[-1]
                    newprog.append(Instruction('EXCH',(goingin,goingout)))
                    old2new[goingout],old2new[goingin] = old2new[goingin],old2new[goingout]
                    val=goingout
                else:
                    val=goingin
                pipe=[val]+pipe

                if len(pipe)>nreg:
                    pipe.pop()   #this value fell out of the pipe
                assert len(pipe)<=nreg
            #now we can emit the command with registers remapped
            rm=regmap(old2new)
            newprog.append(cmd.renumber(rm))
    return newprog



class Machine:

    def RunProgram(cls,commands,args=[],tracing=False):
        nreg=maxRegister(commands)
        machine=Machine(nreg,args)
        machine._tracing = tracing
        ip=0
        if tracing:
            print 'args', args
        while not machine.stopped():
            if ip>=len(commands):
                return None
            cmd=commands[ip]
            if isinstance(cmd,str):
                pass
            elif cmd.name=='J':
                ip=commands.index(cmd.arguments[0])
            elif cmd.name=='JT':
                c = machine.creg()
                assert c is not None
                if c:
                    ip=commands.index(cmd.arguments[0])
            else:
                machine.op(cmd.name,*cmd.arguments)
            ip+=1
        if tracing:
            print 'ret', machine._retval
        return machine._retval
    RunProgram=classmethod(RunProgram)


    def __init__(self,nreg,args):
        self._nreg=nreg
        self._args=args
        self._stopped=False
        self._creg=None
        self._tracing = False
        self._registers=[None for x in range(nreg+1)]

    def creg(self):
        return self._creg

    def registers(self):
        return self._registers[1:]

    def register(self, reg):
        v = self._registers[reg]
        assert v is not None
        return v

    def stopped(self):
        return self._stopped

    def op(self,opcode,*operands):
        if self._tracing:
            args = []
            for arg in operands:
                if isinstance(arg, int):
                    args.append('r%s=%s'%(arg, self._registers[arg]))
                else:
                    args.append(arg)
            #print opcode, ', '.join(map(str, args))
            #will want to trap later to defer unimplemented to the LLInterpreter...
        m = getattr(self,opcode,None)
        if m is not None:
            m(*operands)
        else:
            self.llop(opcode, *operands)

    def RETPYTHON(self,reg):
        self._stopped=True
        self._retval=self.register(reg)

    def LIA(self,destination,argindex):
        self._registers[destination]=self._args[argindex.value]

    def LOAD(self,destination,immed):
        self._registers[destination]=immed.value

    def MOV(self,destination,source):
        self._registers[destination]=self.register(source)

    def EXCH(self,destination,source):
        #self._registers[destination],self._registers[source]=self.register(source),self.register(destination)
        self._registers[destination],self._registers[source]=self._registers[source],self._registers[destination]


    def int_gt(self,rega,regb):
        self._creg = self.register(rega) > self.register(regb)

    def int_lt(self,rega,regb):
        self._creg = self.register(rega) < self.register(regb)

    def int_ge(self,rega,regb):
        self._creg = self.register(rega) >= self.register(regb)

    def int_le(self,rega,regb):
        self._creg = self.register(rega) <= self.register(regb)

    def int_eq(self,rega,regb):
        self._creg = self.register(rega) == self.register(regb)

    def int_ne(self,rega,regb):
        self._creg = self.register(rega) != self.register(regb)


    def llop(self, opcode, destination, *sources):
        sourcevalues = []
        for r in sources:
            sourcevalues.append(self.register(r))
        self._registers[destination] = LLFrame.__dict__['op_'+opcode](None, *sourcevalues)





