"""
Some simple classes that output LLVM-assembler.
"""

import autopath

import exceptions

from pypy.objspace.flow.model import Variable, Constant, SpaceOperation


class Function(object):
    def __init__(self, funcdef, startbb):
        self.funcdef = funcdef
        self.startbb = startbb
        self.blocks = {}

    def basic_block(self, block):
        assert block.label != self.startbb.label, "Block has same label as startblock!"
        self.blocks[block.label] = block

    def __str__(self):
        r = [self.funcdef, " {\n", str(self.startbb)]
        r += [str(bb) for bb in self.blocks.values()] + ["}\n\n"]
        return "".join(r)

class BasicBlock(object):
    def __init__(self, label):
        self.label = label
        self.instructions = []

    def instruction(self, instr): #should not be used
        self.instructions.append(instr)

    def select(self, l_arg, l_select, l_v1, l_v2):
        s = "%s = select bool %s, %s, %s"
        s = s % (l_arg.llvmname(), l_select.llvmname(), l_v1.typed_name(),
                 l_v2.typed_name())
        self.instructions.append(s)               

    def phi(self, l_arg, l_values, blocks):
        assert len(l_values) == len(blocks)
        vars_string = []
        print "inserting phi node", l_arg, l_values, blocks
        print l_arg.llvmname(), l_arg.llvmtype()
        fd = "" + "%s = phi %s " % (l_arg.llvmname(), l_arg.llvmtype())
        fd += ", ".join(["[%s, %s]" % (v.llvmname(), b)
               for v, b in zip(l_values, blocks)])
        self.instructions.append(fd)

    def spaceop(self, l_target, opname, l_args):
        if l_target.llvmtype() == "void":
            s = "call void %%std.%s(" % opname
        else:
            s = "%s = call %s %%std.%s(" % (l_target.llvmname(),
                                        l_target.llvmtype(), opname)
        self.instructions.append(s +
            ", ".join([a.typed_name() for a in l_args]) + ")")
        
    def call(self, l_target, l_func, l_args):
        if l_target.llvmtype() == "void":
            s = "call void %s(" % l_func.llvmname()
        elif  l_target.llvmtype() == "%std.void":
            s = "call %std.void %s(" % l_func.llvmname()
        else:
            s = "%s = call %s %s(" % (l_target.llvmname(), l_target.llvmtype(),
                                      l_func.llvmname())
        self.instructions.append(s + 
            ", ".join([a.typed_name() for a in l_args]) + ")")

    def call_void(self, l_func, l_args):
        s = "call %s %s(" % (l_func.rettype(), l_func.llvmname())
        self.instructions.append(s +
            ", ".join([a.typed_name() for a in l_args]) + ")")

    def ret(self, l_value):
        self.instructions.append("ret %s" % l_value.typed_name())

    def uncond_branch(self, block):
        self.instructions.append("br label " + block)

    def cond_branch(self, l_switch, blocktrue, blockfalse):
        s = "br %s, label %s, label %s" % (l_switch.typed_name(),
                                           blocktrue, blockfalse)
        self.instructions.append(s)

    def switch(self, l_switch, default, rest=None):
        s = "switch %s, label %s " % (l_switch.typed_name(), default)
        if rest is not None:
            s += "[" + "\n\t".join(["%s %s, label %s" % (l_switch.llvmtype(),
                                                       c, l)
                                  for c, l in rest]) + "]"
        self.instructions.append(s)

    def malloc(self, l_target, l_type, num=1):
        s = "%s = malloc %s" % (l_target.llvmname(),
                                l_type.llvmname_wo_pointer())
        if num > 1:
            s += ", uint %i" % num
        self.instructions.append(s)

    def getelementptr(self, l_target, l_ptr, adresses):
        s = "%s = getelementptr %s %s, " % (l_target.llvmname(),
                                            l_ptr.llvmtype(), l_ptr.llvmname())
        adr = []
        for a in adresses:
            try:
                t = a.typed_name()
                adr.append(t)
            except AttributeError:
                if a >= 0:
                    adr.append("uint %i" % a)
                else:
                    adr.append("int %i" % a)
        self.instructions.append(s + ", ".join(adr))

    def load(self, l_target, l_pter):
        s = "%s = load %s %s" % (l_target.llvmname(), l_pter.llvmtype(),
                                  l_pter.llvmname())
        self.instructions.append(s)

    def store(self, l_value, l_pter):
        s = "store %s, %s" % (l_value.typed_name(), l_pter.typed_name())
        self.instructions.append(s)

    def cast(self, l_target, l_value):
        s = "%s = cast %s to %s" % (l_target.llvmname(), l_value.typed_name(),
                                    l_target.llvmtype())
        self.instructions.append(s)

    def __str__(self):
        s = [self.label + ":\n"]
        for ins in self.instructions:
            s += ["\t%s\n" % ins]
        return "".join(s)


class TryBasicBlock(BasicBlock):
    def __init__(self, label, regularblock, exceptblock):
        self.label = label
        self.exceptblock = exceptblock
        self.regularblock = regularblock
        self.llvmblocks = []
        self.instructions = []
        self.finalized = False

    def invoke(self, l_target, l_func, l_args):
        if l_target.llvmtype() == "void":
            s = "invoke void %s(" % l_func.llvmname()
        elif  l_target.llvmtype() == "%std.void":
            s = "invoke %std.void %s(" % l_func.llvmname()
        else:
            s = "%s = invoke %s %s(" % (l_target.llvmname(),
                                        l_target.llvmtype(), l_func.llvmname())
        s += ", ".join([a.typed_name() for a in l_args]) + ")"
        s += "\n\t\tto label %s.%i\n\t\texcept label %s" % \
             (self.label, len(self.llvmblocks), self.exceptblock)
        self.instructions.append(s)
        self.llvmblocks.append(self.instructions)
        self.instructions = []

    def invoke_void(self, l_func, l_args):
        s = "call %s %s(" % (l_func.rettype(), l_func.llvmname())
        s += ", ".join([a.typed_name() for a in l_args]) + ")"
        s += "\n\t\tto label %s.%i\n\t\texcept label %s" % \
             (self.label, len(self.llvmblocks), self.exceptblock)
        self.instructions.append(s)
        self.llvmblocks.append(self.instructions)
        self.instructions = []

    def __str__(self):
        if not self.finalized:
            self.uncond_branch(self.regularblock)
            self.llvmblocks.append(self.instructions)
            self.instructions = []
            self.finalized = True
        s = []
        for i, instrs in enumerate(self.llvmblocks):
            if i == 0:
                label = self.label
            else:
                label = "%s.%i" % (self.label, i - 1)
            s.append(label + ":\n")
            for ins in instrs:
                s.append("\t%s\n" % ins)
        return "".join(s)
            
            
