from pypy.jit.backend.arm import conditions as cond
from pypy.jit.backend.arm import instructions
# move table lookup out of generated functions
def define_load_store_func(name, table):
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
                    | imm_operation(rt, rn, imm))
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
                        | reg_operation(rt, rn, rm, imm, s, shifttype))
    return f
def define_data_proc_imm(name, table):
    n = (0x1 << 25
        | (table['op'] & 0x1F) << 20)
    if table['result'] and table['base']:
        def imm_func(self, rd, rn, imm=0, cond=cond.AL, s=0):
            if imm < 0:
                raise ValueError
            # XXX check condition on rn
            self.write32(n
                | cond << 28
                | s << 20
                | imm_operation(rd, rn, imm))
    elif not table['base']:
        def imm_func(self, rd, imm=0, cond=cond.AL, s=0):
            # XXX check condition on rn
            self.write32(n
                | cond << 28
                | s << 20
                | imm_operation(rd, 0, imm))
    else:
        def imm_func(self, rn, imm=0, cond=cond.AL, s=0):
            # XXX check condition on rn
            self.write32(n
                | cond << 28
                | s << 20
                | imm_operation(0, rn, imm))
    return imm_func

def define_data_proc(name, table):
    n = ((table['op1'] & 0x1F) << 20
        | (table['op2'] & 0x1F) << 7
        | (table['op3'] & 0x3) << 5)
    if name[-2:] == 'ri':
        def f(self, rd, rm, imm=0, cond=cond.AL, s=0):
            if table['op2cond'] == '!0':
                assert imm != 0
            elif table['op2cond'] == '0':
                assert imm == 0
            self.write32(n
                        | cond << 28
                        | (s & 0x1) << 20
                        | (rd & 0xFF) << 12
                        | (imm & 0x1F) << 7
                        | (rm & 0xFF))

    elif not table['result']:
        # ops without result
        def f(self, rn, rm, imm=0, cond=cond.AL, s=0, shifttype=0):
            self.write32(n
                        | cond << 28
                        | reg_operation(0, rn, rm, imm, s, shifttype))
    elif not table['base']:
        # ops without base register
        def f(self, rd, rm, imm=0, cond=cond.AL, s=0, shifttype=0):
            self.write32(n
                        | cond << 28
                        | reg_operation(rd, 0, rm, imm, s, shifttype))
    else:
        def f(self, rd, rn, rm, imm=0, cond=cond.AL, s=0, shifttype=0):
            self.write32(n
                        | cond << 28
                        | reg_operation(rd, rn, rm, imm, s, shifttype))
    return f

def define_data_proc_register_shifted(name, table):
    n = ((0x1 << 4) | (table['op1'] & 0x1F) << 20 | (table['op2'] & 0x3) << 5)
    if 'result' in table and not table['result']:
        result = False
    else:
        result = True
    if name[-2:] == 'sr':
        if result:
            def f(self, rd, rn, rm, rs, cond=cond.AL, s=0, shifttype=0):
                self.write32(n
                            | cond << 28
                            | (s & 0x1) << 20
                            | (rn & 0xF) << 16
                            | (rd & 0xF) << 12
                            | (rs & 0xF) << 8
                            | (shifttype & 0x3) << 5
                            | (rm & 0xF))
        else:
            def f(self, rn, rm, rs, cond=cond.AL, s=0, shifttype=0):
                self.write32(n
                            | cond << 28
                            | (s & 0x1) << 20
                            | (rn & 0xF) << 16
                            | (rs & 0xF) << 8
                            | (shifttype & 0x3) << 5
                            | (rm & 0xF))
    else:
        def f(self, rd, rn, rm, cond=cond.AL, s=0):
            self.write32(n
                        | cond << 28
                        | (s & 0x1) << 20
                        | (rd & 0xF) << 12
                        | (rm & 0xF) << 8
                        | (rn & 0xF))
    return f

def define_supervisor_and_coproc(name, table):
    n = (0x3 << 26 | (table['op1'] & 0x3F) << 20 | (table['op'] & 0x1) << 4)
    def f(self, coproc, opc1, rt, crn, crm, opc2=0, cond=cond.AL):
        self.write32(n
                    | cond << 28
                    | (opc1 & 0x7) << 21
                    | (crn & 0xF) << 16
                    | (rt & 0xF) << 12
                    | (coproc & 0xF) << 8
                    | (opc2 & 0x7) << 5
                    | (crm & 0xF))
    return f

def define_multiply_instructions(name, table):
    n = (table['op'] & 0xF) << 20 | 0x9 << 4
    if 'acc' in table and table['acc']:
        def f(self, rd, rn, rm, ra, cond=cond.AL, s=0):
            self.write32(n
                        | cond << 28
                        | (s & 0x1)
                        | (rd & 0xF) << 16
                        | (ra & 0xF) << 12
                        | (rm & 0xF) << 8
                        | (rn & 0xF))
    elif 'long' in table and table['long']:
       def f(self, rdhi, rdlo, rn, rm, cond=cond.AL, s=0):
            assert rdhi != rdlo
            self.write32(n
                        | cond << 28
                        | (s & 0x1)
                        | (rdhi & 0xF) << 16
                        | (rdlo & 0xF) << 12
                        | (rm & 0xF) << 8
                        | (rn & 0xF))
    else:
        def f(self, rd, rn, rm, cond=cond.AL, s=0):
            self.write32(n
                        | cond << 28
                        | (s & 0x1)
                        | (rd & 0xF) << 16
                        | (rm & 0xF) << 8
                        | (rn & 0xF))

    return f

def define_long_mult_div_instructions(name, table):
    pass
def imm_operation(rt, rn, imm):
    return ((rn & 0xFF) << 16
    | (rt & 0xFF) << 12
    | (imm & 0xFFF))

def reg_operation(rt, rn, rm, imm, s, shifttype):
    # XXX encode shiftype correctly
    return ((s & 0x1) << 20
            | (rn & 0xFF) << 16
            | (rt & 0xFF) << 12
            | (imm & 0x1F) << 7
            | (shifttype & 0x3) << 5
            | (rm & 0xFF))

def define_instruction(builder, key, val, target):
        f = builder(key, val)
        setattr(target, key, f)

def define_instructions(target):
    i_g_map = [(instructions.load_store, define_load_store_func),
                (instructions.data_proc, define_data_proc),
                (instructions.data_proc_imm, define_data_proc_imm),
                (instructions.supervisor_and_coproc, define_supervisor_and_coproc),
                (instructions.multiply, define_multiply_instructions),
                (instructions.data_proc_reg_shift_reg, define_data_proc_register_shifted)]

    for inss, gen in i_g_map:
        for key, val in inss.iteritems():
            define_instruction(gen, key, val, target)
