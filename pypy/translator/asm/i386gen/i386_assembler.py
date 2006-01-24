"""i386 Basic assembler...
Designed to mirror the PPC assembler system, operands added as required.

Current system needs to assemble given, code, link into python, and return python
callabale.  (Stub routine currently given).

"""

class i386Assembler:

    def __init__(self):
        self._opcodes=[]

    def __getattr__(self,attr):
        def func(*args):
            return self.op(attr,args)
        return func

    def op(self,opcode,*args):
        self._opcodes.append((opcode,args))

    def Make_func(cls,assembler,input='ii',output='i'):
        return lambda x,y:x+y+1

    Make_func=classmethod(Make_func)

    def dump(self):
        l=1000
        for op in self._opcodes:
            print '>>%d :%s' %(l,str(op))
            l+=1

make_func=i386Assembler.Make_func


if __name__=='__main__':
    a=i386Assembler()
    a.op('mov','ax,''bx')

    a.mov('spi','esi')
    print a._opcodes
    a.dump()


