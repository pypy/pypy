from pypy.annotation.pairtype import extendabletype

class Instruction(object):
    __metaclass__ = extendabletype
    
    def registers_used(self):
        return [self.target_register()] + list(self.source_registers())

    def target_register(self):
        pass

    def source_registers(self):
        pass

    def renumber(self, map):
        pass

    def execute(self, machine):
        assert not "not here"

    def __repr__(self):
        args = []
        for k, v in self.__dict__.iteritems():
            args.append('%s=%r'%(k, v))
        return '%s(%s)'%(self.__class__.__name__, ', '.join(args))


class LLInstruction(Instruction):
    def __init__(self, opname, dest, *sources):
        self.opname = opname
        self.dest = dest
        self.sources = sources

    def target_register(self):
        return self.dest

    def source_registers(self):
        return self.sources

    def renumber(self, map):
        return LLInstruction(self.opname,
                             map[self.dest],
                             *[map[s] for s in self.sources])

    def _frame(self):
        try:
            _frame_type = LLInstruction._frame_type
        except AttributeError:
            from pypy.rpython.llinterp import LLFrame
            _frame_type = LLInstruction._frame_type = type('*frame*', (),
                                                           LLFrame.__dict__.copy())
        return object.__new__(_frame_type)

    def execute(self, machine):
        sources = map(machine.get_register, self.sources)
        result = getattr(self._frame(), 'op_' + self.opname)(*sources)
        machine.store_register(self.dest, result)


class LOAD_IMMEDIATE(Instruction):
    def __init__(self, target, immed):
        self.target = target
        self.immed = immed

    def target_register(self):
        return self.target

    def source_registers(self):
        return []

    def renumber(self, map):
        return LOAD_IMMEDIATE(map[self.target], self.immed)

    def execute(self, machine):
        machine.store_register(self.target, self.immed)


class LOAD_ARGUMENT(Instruction):
    def __init__(self, target, argindex):
        self.target = target
        self.argindex = argindex

    def target_register(self):
        return self.target

    def source_registers(self):
        return []

    def renumber(self, map):
        return LOAD_ARGUMENT(map[self.target], self.argindex)

    def execute(self, machine):
        machine.store_register(self.target, machine.args[self.argindex])


class MOVE(Instruction):
    def __init__(self, target, source):
        self.target = target
        self.source = source

    def target_register(self):
        return self.target

    def source_registers(self):
        return [self.source]

    def renumber(self, map):
        return MOVE(map[self.target], map[self.source])

    def execute(self, machine):
        machine.store_register(self.target, machine.get_register(self.source))
    

class RETPYTHON(Instruction):
    def __init__(self, source):
        self.source = source

    def target_register(self):
        return None

    def source_registers(self):
        return [self.source]

    def renumber(self, map):
        return RETPYTHON(map[self.source])

    def execute(self, machine):
        machine.retval = machine.get_register(self.source)
        machine.stopped = True


class ControlFlowInstruction(Instruction):
    def registers_used(self):
        return []

    def target_register(self):
        return None

    def source_registers(self):
        return []

    def renumber(self, map):
        return self


class Label(ControlFlowInstruction):
    def __init__(self, name):
        self.name = name

    def execute(self, machine):
        pass
    

class Jump(ControlFlowInstruction):
    def __init__(self, target):
        self.target = target

    def do_jump(self, machine):
        for i, insn in enumerate(machine.insns):
            print i, insn
            if isinstance(insn, Label):
                if insn.name == self.target:
                    break
        else:
            raise Exception, ""
        machine.program_counter = i


class JUMP(Jump):
    def execute(self, machine):
        self.do_jump(machine)


class ConditionalJump(Jump):
    def __init__(self, source, target):
        self.source = source
        self.target = target

    def source_registers(self):
        return [self.source]

    def renumber(self, map):
        return self.__class__(map[self.source], self.target)


class JUMP_IF_TRUE(ConditionalJump):
    def execute(self, machine):
        val = machine.get_register(self.source)
        assert isinstance(val, bool)
        if val:
            self.do_jump(machine)


class JUMP_IF_FALSE(ConditionalJump):
    def execute(self, machine):
        val = machine.get_register(self.source)
        assert isinstance(val, bool)
        if not val:
            self.do_jump(machine)


class STORE_STACK(Instruction):
    def __init__(self, stackindex, source):
        self.stackindex = stackindex
        self.source = source

    def target_register(self):
        return None

    def source_registers(self):
        return [self.source]

    def renumber(self, map):
        return STORESTACK(stackindex, map[source])

    def execute(self, machine):
        machine.stack[self.stackindex] = machine.get_register(self.source)


class LOAD_STACK(Instruction):
    def __init__(self, target, stackindex):
        self.target = target
        self.stackindex = stackindex

    def target_register(self):
        return self.target

    def source_registers(self):
        return []

    def renumber(self, map):
        return LOADSTACK(map[self.target], self.stackindex)

    def execute(self, machine):
        machine.store_register(self.target, machine.stack[self.stackindex])


class Machine(object):
    def __init__(self, insns, nreg=None, tracing=False):
        self.insns = insns
        self.nreg = nreg
        self.tracing = tracing

    def execute(self, *args):
        self.stopped = False
        self.registers = {}
        self.stack = {}
        self.program_counter = 0
        self.args = args
        if hasattr(self, 'retval'):
            del self.retval
        
        while not self.stopped:
            insn = self.insns[self.program_counter]
            if self.tracing:
                print self.program_counter, insn,
                t = insn.target_register()
                if t is not None:
                    print t, '<-', 
                print ', '.join(map(
                    str, map(self.get_register, insn.source_registers())))
            insn.execute(self)
            self.program_counter += 1
        return self.retval

    def store_register(self, reg, value):
        self.registers[reg] = value

    def get_register(self, reg):
        return self.registers[reg]

