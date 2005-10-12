""" IRM Simulator """
import autopath
from pypy.rpython.llinterp import LLFrame
from pypy.translator.asm.infregmachine import Instruction
from pypy.objspace.flow.model import Constant

class Machine:

    def RunProgram(cls,commands,args=[],nreg=10,tracing=False):
        #run this program
        machine=Machine(nreg,args)
        machine._tracing = tracing
        ip=0
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
            print opcode, ', '.join(map(str, args))
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
        self._registers[destination],self._registers[source]=self.register(source),self.register(destination)

    def int_gt(self,rega,regb):
        self._creg = self.register(rega) > self.register(regb)

    def llop(self, opcode, destination, *sources):
        sourcevalues = []
        for r in sources:
            sourcevalues.append(self.register(r))
        self._registers[destination] = LLFrame.__dict__['op_'+opcode](None, *sourcevalues)


