import autopath
from pypy.translator.flowmodel import *

class Op:
    def __init__(self, gen, op):
        self.str = gen.str
        self.opname = op.opname
        self.args = op.args
        self.result = op.result
    def __call__(self):
        if self.opname in self.binary_ops:
            self.op_binary(self.opname)
        else:
            self.op_default()
    binary_ops = {
        "add": "+",
        "mod": "mod",
    }
    def op_default(self):
        print "; Op", self.opname, "is missing"
    def op_binary(self, op):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        cl_op = self.binary_ops[op]
        print "(setq", s(result), "(", cl_op, s(arg1), s(arg2), "))"

class GenCL:
    def __init__(self, fun):
        self.fun = fun
        self.blockref = {}
    def str(self, obj):
        if isinstance(obj, Variable):
            return obj.pseudoname
        elif isinstance(obj, Constant):
            return self.conv(obj.value)
        else:
            return "#<" # unreadable
    def conv(self, val):
        if val is None:
            return "nil"
        elif isinstance(val, int):
            return str(val)
        else:
            return "#<" # unreadable
    def emitcode(self):
        import sys
        from cStringIO import StringIO
        out = StringIO()
        sys.stdout = out
        self.emit()
        sys.stdout = sys.__stdout__
        return out.getvalue()
    def emit(self):
        self.emit_defun(self.fun)
    def emit_defun(self, fun):
        print "(defun", fun.functionname, "(",
        for arg in fun.get_args():
            print self.str(arg),
        print ")"
        print "(block nil"
        self.emit_block(fun.startblock)
        print ")"
        print ")"
    def emit_block(self, block):
        print "(tagbody"
        nb = len(self.blockref)
        tag = self.blockref.setdefault(block, nb)
        if tag != nb:
            print "(go", "tag" + str(tag), ")"
            print ")" # close tagbody
            return
        print "tag" + str(tag)
        for op in block.operations:
            emit_op = Op(self, op)
            emit_op()
        self.dispatch_branch(block.branch)
        print ")"
    def dispatch_branch(self, branch):
        if isinstance(branch, Branch):
            self.emit_branch(branch)
        elif isinstance(branch, ConditionalBranch):
            self.emit_conditional_branch(branch)
        elif isinstance(branch, EndBranch):
            self.emit_end_branch(branch)
        else:
            print branch.__class__, "is missing"
    def emit_branch(self, branch):
        if branch.target.has_renaming:
            source = branch.args
            target = branch.target.input_args
            print "(psetq",   # parallel assignment
            for item in zip(source, target):
                init, var = map(self.str, item)
                print var, init,
            print ")"
        self.emit_block(branch.target)
    def emit_conditional_branch(self, branch):
        print "(if"
        self.emit_truth_test(branch.condition)
        self.emit_branch(branch.ifbranch)
        self.emit_branch(branch.elsebranch)
        print ")"
    def emit_end_branch(self, branch):
        retval = self.str(branch.returnvalue)
        print "(return", retval, ")"
    def emit_truth_test(self, obj):
        # XXX: Fix this
        print "(not (zerop", self.str(obj), "))"
