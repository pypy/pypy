import autopath
from pypy.translator.flowmodel import *
from pypy.translator.annotation import Annotator

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
        self.annotate([])
    def annotate(self, input_arg_types):
        ann = Annotator(self.fun)
        ann.build_types(input_arg_types)
        ann.simplify()
        self.ann = ann
    def str(self, obj):
        if isinstance(obj, Variable):
            return obj.pseudoname
        elif isinstance(obj, Constant):
            return self.conv(obj.value)
        else:
            return "#<"
    def conv(self, val):
        if val is None:
            return "nil"
        elif isinstance(val, bool): # should precedes int
            if val:
                return "t"
            else:
                return "nil"
        elif isinstance(val, int):
            return str(val)
        else:
            return "#<"
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
        self.cur_block = block
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
            print "(psetq", # parallel assignment
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
        annset = self.ann.annotated[self.cur_block]
        tp = annset.get_type(obj)
        s = self.str
        if tp is bool:
            print s(obj)
        elif tp is int:
            print "(not (zerop", s(obj), "))"
        else:
            print self.template(s(obj), [
                "(typecase %",
                "(boolean %)",
                "(fixnum (not (zerop %)))",
                ")"])
    def template(self, sub, seq):
        def _(x):
            return x.replace("%", sub)
        return "\n".join(map(_, seq))
