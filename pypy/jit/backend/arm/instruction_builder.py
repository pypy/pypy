from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import instructions

def define_load_store_func(target, name, table):
    #  XXX W and P bits are not encoded yet
    n = (0x1 << 26
        | (table['A'] & 0x1) << 25
        | (table['op1'] & 0x1F) << 20
        | (table['B'] & 0x1) << 4)
    if table['imm']:
        def f(self, rt, rn, imm=0, cond=cond.AL):
            p = 1
            w = 0
            u, imm = self._encode_imm(imm)
            self.write32(n
                    | cond << 28
                    | (p & 0x1) <<  24
                    | (u & 0x1) << 23
                    | (w & 0x1) << 21
                    | (rn & 0xFF) << 16
                    | (rt & 0xFF) << 12
                    | (imm & 0xFFF))
    else:
        def f(self, rt, rn, rm, imm=0, cond=cond.AL, s=0, shifttype=0):
            p = 1
            w = 0
            u, imm = self._encode_imm(imm)
            self.write32(n
                        | cond << 28
                        | (p & 0x1) <<  24
                        | (u & 0x1) << 23
                        | (w & 0x1) << 21
                        | (rn & 0xFF) << 16
                        | (rt & 0xFF) << 12
                        | (imm & 0x1F) << 7
                        | (shifttype & 0x3) << 5
                        | (rm & 0xFF))

    setattr(target, name, f)

def define_instructions(target):
    for key, val in instructions.load_store.iteritems():
        define_load_store_func(target, key, val)
