from pypy.objspace.flow.model import *
from pypy.translator.annrpython import RPythonAnnotator

from pypy.translator.simplify import simplify_graph
from pypy.translator.transform import transform_graph


DEBUG = False


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
        if DEBUG:
            self.op_default()
            return
        if self.opname in self.binary_ops:
            self.op_binary(self.opname)
        else:
            default = self.op_default
            meth = getattr(self, "op_" + self.opname, default)
            meth()
    def op_default(self):
        print ";;", self.op
        print ";; Op", self.opname, "is missing"
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
    def op_contains(self):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        print "(setq", s(result), "(not (not (find", s(arg2), s(arg1), "))))"
    def op_add(self):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        print "(setq", s(result)
        table = {
            (int, int): "(+ %s %s)",
            (int, long): "(+ %s %s)",
            (long, int): "(+ %s %s)",
            (long, long): "(+ %s %s)",
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
            (long,): "(zerop %s)",
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
            (long,): "(not (zerop %s))",
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
    def op_next(self):
        s = self.str
        result, (iterator,) = self.result, self.args
        print "(let ((result (funcall", s(iterator), ")))"
        print "  (setq", s(result), "(car result))"
        print "  (setq last-exc (cdr result)))"
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
    def op_pow(self):
        s = self.str
        result, (x,y,z) = self.result, self.args
        print "(setq", s(result)
        table = {
            (int, int, type(None)): (lambda args: args[:2], "(expt %s %s)"),
        }
        self.gen.emit_typecase(table, x, y, z)
        print ")"

class GenCL:
    def __init__(self, fun, input_arg_types=[]):
        simplify_graph(fun)
        self.fun = fun
        self.blockref = {}
        self.annotate(input_arg_types)
        transform_graph(self.ann)
    def annotate(self, input_arg_types):
        ann = RPythonAnnotator()
        ann.build_types(self.fun, input_arg_types)
        self.setannotator(ann)
    def setannotator(self, annotator):
        self.ann = annotator
    def get_type(self, var):
        return self.ann.gettype(var)
    def str(self, obj):
        if isinstance(obj, Variable):
            return obj.name
        elif isinstance(obj, Constant):
            return self.conv(obj.value)
        else:
            return "#<%r>" % (obj,)
    def conv(self, val):
        if isinstance(val, tuple):
            val = map(self.conv, val)
            return "'(%s)" % ' '.join(val)
        elif isinstance(val, bool): # should precedes int
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
        elif isinstance(val, type(Exception)) and issubclass(val, Exception):
            return "'%s" % val.__name__
        elif val is last_exception:
            return "last-exc"
        elif val is last_exc_value:
            return "'last-exc-value"
        else:
            return "#<%r>" % (val,)
    def emitcode(self, public=True):
        import sys
        from cStringIO import StringIO
        out = StringIO()
        oldstdout = sys.stdout
        sys.stdout = out
        self.emit()
        sys.stdout = oldstdout
        return out.getvalue()
    def emit(self):
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
        vardict = {}
        for block in blocklist:
            tag = len(self.blockref)
            self.blockref[block] = tag
            for var in block.getvariables():
                vardict[var] = self.get_type(var)
        print "( last-exc",
        for var in vardict:
            if var in arglist:
                print "(", self.str(var), self.str(var), ")",
            else:
                print self.str(var),
        print ")"
        print ";; DEBUG: type inference"
        for var in vardict:
            tp = vardict[var]
            if tp:
                print ";;", self.str(var), "is", tp.__name__
        print "(setq last-exc nil)"
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
            if (len(exits) == 2 and
                exits[0].exitcase == False and
                exits[1].exitcase == True):
                print "(if", self.str(block.exitswitch)
                print "(progn"
                self.emit_link(exits[1])
                print ") ; else"
                print "(progn"
                self.emit_link(exits[0])
                print "))"
            else:
                # this is for the more general case.  The previous special case
                # shouldn't be needed but in Python 2.2 we can't tell apart
                # 0 vs nil  and  1 vs t  :-(
                for exit in exits[:-1]:
                    print "(if (equalp", self.str(block.exitswitch),
                    print self.conv(exit.exitcase), ')'
                    print "(progn"
                    self.emit_link(exit)
                    print ")"
                print "(progn ; else should be", self.conv(exits[-1].exitcase)
                self.emit_link(exits[-1])
                print ")" * len(exits)
        elif len(block.inputargs) == 2:    # exc_cls, exc_value
            exc_cls   = self.str(block.inputargs[0])
            exc_value = self.str(block.inputargs[1])
            print "(something-like-throw-exception %s %s)" % (exc_cls, exc_value)
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
        for s, t in zip(source, target):
            if s != t and s != Constant(undefined_value):
                print self.str(t), self.str(s),
        print ")"
        self.emit_jump(link.target)
    typemap = {
        bool: "boolean",
        int: "fixnum",
        long: "bignum",
        type(''): "string", # hack, 'str' is in the namespace!
        list: "vector",
    }
    def emit_typecase(self, table, *args):
        argreprs = tuple(map(self.str, args))
        argtypes = tuple(map(self.get_type, args))
        if argtypes in table:
            trans = table[argtypes]
            if isinstance(trans, tuple): # (manip-args, code-template)
                manip, trans = trans
                argreprs = manip(argreprs)                
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
    def globaldeclarations(self):
        return prelude


prelude = """;;;; Prelude
(defun make-iterator (seq)
  (let ((i 0))
    (lambda ()
      (if (< i (length seq))
          (let ((v (elt seq i))) (incf i) (cons v nil))
          (cons nil 'StopIteration)))))
(defun python-slice (seq start end)
  (let ((l (length seq)))
    (if (not start) (setf start 0))
    (if (not end) (setf end l))
    (if (minusp start) (incf start l))
    (if (minusp end) (incf end l))
    (subseq seq start end)))
;; temporary
(defun python-range (end)
  (let ((a (make-array end)))
    (loop for i below end
          do (setf (elt a i) i)
          finally (return a))))
"""
