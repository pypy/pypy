import autopath
from pypy.objspace.flow.model import *
from pypy.translator.annotation import Annotator

from pypy.translator.simplify import simplify_graph
from pypy.translator.transform import transform_graph


# XXX For 2.2 the emitted code isn't quite right, because we cannot tell
# when we should write "0"/"1" or "nil"/"t".
if not isinstance(bool, type):
    class bool(int):
        pass


class Op:
    def __init__(self, gen, op):
        self.gen = gen
        self.str = gen.str
        self.op = op
        self.opname = op.opname
        self.args = op.args
        self.result = op.result
    def __call__(self):
        if self.opname in self.binary_ops:
            self.op_binary(self.opname)
        else:
            default = self.op_default
            meth = getattr(self, "op_" + self.opname, default)
            meth()
    def op_default(self):
        print ";", self.op
        print "; Op", self.opname, "is missing"
    binary_ops = {
        #"add": "+",
        "sub": "-",
        "inplace_add": "+", # weird, but it works
        "inplace_lshift": "ash",
        "mod": "mod",
        "lt": "<",
        "le": "<=",
        "eq": "=",
        "gt": ">",
        "and_": "logand",
        "getitem": "elt",
    }
    def op_binary(self, op):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        cl_op = self.binary_ops[op]
        print "(setq", s(result), "(", cl_op, s(arg1), s(arg2), "))"
    def op_add(self):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        print "(setq", s(result)
        table = {
            (int, int): "(+ %s %s)",
            (str, str): "(concatenate 'string %s %s)",
            (list, list): "(concatenate 'vector %s %s)",
        }
        self.gen.emit_typecase(table, arg1, arg2)
        print ")"
    def op_not_(self):
        s = self.str
        result, (arg1,) = self.result, self.args
        print "(setq", s(result), "(not"
        table = {
            (bool,): "(not %s)",
            (int,): "(zerop %s)",
            (list,): "(zerop (length %s))",
        }
        self.gen.emit_typecase(table, arg1)
        print "))"
    def op_is_true(self):
        s = self.str
        result, (arg1,) = self.result, self.args
        print "(setq", s(result)
        table = {
            (bool,): "%s",
            (int,): "(not (zerop %s))",
            (list,): "(not (zerop (length %s)))",
        }
        self.gen.emit_typecase(table, arg1)
        print ")"
    def op_newtuple(self):
        s = self.str
        print "(setq", s(self.result), "(list",
        for arg in self.args:
            print s(arg),
        print "))"
    def op_newlist(self):
        s = self.str
        print "(setq", s(self.result), "(vector",
        for arg in self.args:
            print s(arg),
        print "))"
    def op_alloc_and_set(self):
        s = self.str
        result, (size, init) = self.result, self.args
        print "(setq", s(result), "(make-array", s(size), "))"
        print "(fill", s(result), s(init), ")"
    def op_setitem(self):
        s = self.str
        (seq, index, element) = self.args
        print "(setf (elt", s(seq), s(index), ")", s(element), ")"
    def op_iter(self):
        s = self.str
        result, (seq,) = self.result, self.args
        print "(setq", s(result), "(make-iterator", s(seq), "))"
    def op_next_and_flag(self):
        s = self.str
        result, (iterator,) = self.result, self.args
        print "(setq", s(result), "(funcall", s(iterator), "))"
    builtin_map = {
        pow: "expt",
        range: "python-range",
    }
    def op_simple_call(self):
        func = self.args[0]
        if not isinstance(func, Constant):
            self.op_default()
            return
        func = func.value
        if func not in self.builtin_map:
            self.op_default()
            return
        s = self.str
        args = self.args[1:]
        print "(setq", s(self.result), "(", self.builtin_map[func],
        for arg in args:
            print s(arg),
        print "))"
    def op_getslice(self):
        s = self.str
        result, (seq, start, end) = self.result, self.args
        print "(setq", s(result), "(python-slice", s(seq), s(start), s(end), "))"


class GenCL:
    def __init__(self, fun, input_arg_types=[]):
        simplify_graph(fun)
        self.fun = fun
        self.blockref = {}
        self.annotate(input_arg_types)
        transform_graph(self.ann)
    def annotate(self, input_arg_types):
        ann = Annotator(self.fun)
        ann.build_types(input_arg_types)
        ann.simplify()
        self.ann = ann
    def cur_annset(self):
        return self.ann.annotated[self.cur_block]
    def str(self, obj):
        if isinstance(obj, Variable):
            return obj.name
        elif isinstance(obj, Constant):
            return self.conv(obj.value)
        else:
            return "#<"
    def conv(self, val):
        if isinstance(val, bool): # should precedes int
            if val:
                return "t"
            else:
                return "nil"
        elif isinstance(val, (int, long)):
            return str(val)
        elif val is None:
            return "nil"
        elif isinstance(val, str):
            val.replace("\\", "\\\\")
            val.replace("\"", "\\\"")
            val = '"' + val + '"'
            return val
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
        self.emit_prelude()
        self.emit_defun(self.fun)
    def emit_defun(self, fun):
        print ";;;; Main"
        print "(defun", fun.name
        arglist = fun.getargs()
        print "(",
        for arg in arglist:
            print self.str(arg),
        print ")"
        print "(prog"
        blocklist = []
        def collect_block(node):
            if isinstance(node, Block):
                blocklist.append(node)
        traverse(collect_block, fun)
        varlist = {}
        for block in blocklist:
            tag = len(self.blockref)
            self.blockref[block] = tag
            for var in block.getvariables():
                varlist[var] = None
        varlist = varlist.keys()
        print "(",
        for var in varlist:
            if var in arglist:
                print "(", self.str(var), self.str(var), ")",
            else:
                print self.str(var),
        print ")"
        for block in blocklist:
            self.emit_block(block)
        print ")"
        print ")"
    def emit_block(self, block):
        self.cur_block = block
        tag = self.blockref[block]
        print "tag" + str(tag)
        for op in block.operations:
            emit_op = Op(self, op)
            emit_op()
        exits = block.exits
        if len(exits) == 1:
            self.emit_link(exits[0])
        elif len(exits) > 1:
            # only works in the current special case
            assert len(exits) == 2
            assert exits[0].exitcase == False
            assert exits[1].exitcase == True
            print "(if", self.str(block.exitswitch)
            print "(progn"
            self.emit_link(exits[1])
            print ") ; else"
            print "(progn"
            self.emit_link(exits[0])
            print "))"
        else:
            retval = self.str(block.inputargs[0])
            print "(return", retval, ")"
    def emit_jump(self, block):
        tag = self.blockref[block]
        print "(go", "tag" + str(tag), ")"
    def emit_link(self, link):
        source = link.args
        target = link.target.inputargs
        print "(psetq", # parallel assignment
        for item in zip(source, target):
            init, var = map(self.str, item)
            if var != init:
                print var, init,
        print ")"
        self.emit_jump(link.target)
    typemap = {
        bool: "boolean",
        int: "fixnum",
        type(''): "string", # hack, 'str' is in the namespace!
        list: "vector",
    }
    def emit_typecase(self, table, *args):
        argreprs = tuple(map(self.str, args))
        annset = self.cur_annset()
        argtypes = tuple(map(annset.get_type, args))
        if argtypes in table:
            trans = table[argtypes]
            print trans % argreprs
        else:
            print "(cond"
            for argtypes in table:
                print "((and",
                for tp, s in zip(argtypes, argreprs):
                    cl_tp = "'" + self.typemap[tp]
                    print "(typep", s, cl_tp, ")",
                print ")"
                trans = table[argtypes]
                print trans % argreprs,
                print ")"
            print ")"
    def emit_prelude(self):
        print ";;;; Prelude"
        print prelude


prelude = """\
(defun make-iterator (seq)
  (let ((i 0))
    (lambda ()
      (if (< i (length seq))
          (let ((v (elt seq i))) (incf i) (list v t))
          (list nil nil)))))
(defun python-slice (seq start end)
  (let ((l (length seq)))
    (if (not start) (setf start 0))
    (if (not end) (setf end l))
    (if (minusp start) (incf start l))
    (if (minusp end) (incf end l))
    (subseq seq start end)))
; temporary
(defun python-range (end)
  (let ((a (make-array end)))
    (loop for i below end
          do (setf (elt a i) i))
    a))
"""
