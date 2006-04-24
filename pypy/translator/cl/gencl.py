from pypy.rpython.ootypesystem.ootype import Instance, List
from pypy.translator.cl.clrepr import repr_arg, repr_var, repr_const, repr_fun_name, repr_class_name


class Op:

    def __init__(self, gen, op):
        self.gen = gen
        self.str = repr_arg
        self.op = op
        self.opname = op.opname
        self.args = op.args
        self.result = op.result

    def __iter__(self):
        if self.opname in self.binary_ops:
            for line in self.op_binary(self.opname):
                yield line
        else:
            meth = getattr(self, "op_" + self.opname)
            result = repr_arg(self.result)
            args = map(repr_arg, self.args)
            for line in meth(result, *args):
                yield line

    def op_same_as(self, result, arg):
        yield "(setf %s %s)" % (result, arg)

    binary_ops = {
        #"add": "+",
        "int_add": "+",
        "sub": "-",
        "inplace_add": "+", # weird, but it works
        "inplace_lshift": "ash",
        "mod": "mod",
        "int_mod": "mod",
        "lt": "<",
        "int_lt": "<",
        "le": "<=",
        "eq": "=",
        "int_eq": "=",
        "gt": ">",
        "and_": "logand",
        "getitem": "elt",
    }

    def op_binary(self, op):
        s = self.str
        result, (arg1, arg2) = self.result, self.args
        cl_op = self.binary_ops[op]
        yield "(setf %s (%s %s %s))" % (s(result), cl_op, s(arg1), s(arg2))

    def op_int_is_true(self, result, arg):
        yield "(setf %s (not (zerop %s)))" % (result, arg)

    def op_direct_call(self, result, fun, *args):
        graph = self.args[0].value.graph
        self.gen.pendinggraphs.append(graph)
        args = " ".join(args)
        yield "(setf %s (%s %s))" % (result, fun, args)

    def declare_class(self, cls):
        # cls is really type of Instance
        name = cls._name
        fields = cls._fields
        fieldnames = ['('+field+')' for field in fields.keys()]
        field_declaration = ' '.join(fieldnames)
        class_declaration = "(defclass %s () (%s))" % (repr_class_name(name), field_declaration)
        return class_declaration

    def op_new(self, result, _):
        cls = self.args[0].value
        if isinstance(cls, List):
            yield "(setf %s (make-array 0 :adjustable t))" % (result,)
        else:
            declaration = self.declare_class(cls)
            self.gen.declarations.append(declaration)
            yield "(setf %s (make-instance '%s))" % (result, repr_class_name(cls._name))

    def op_oosend(self, result, *ignore):
        method = self.args[0].value
        receiver = self.args[1]
        args = self.args[2:]
        if isinstance(receiver.concretetype, List):
            impl = ListImpl(receiver)
            code = getattr(impl, method)(*args)
        yield "(setf %s %s)" % (result, code)

    def op_oogetfield(self, result, obj, _):
        fieldname = self.args[1].value
        yield "(setf %s (slot-value %s '%s))" % (result, obj, fieldname)

    def op_oosetfield(self, result, obj, _, value):
        fieldname = self.args[1].value
        if fieldname == "meta": # XXX
            raise StopIteration
        yield "(setf (slot-value %s '%s) %s)" % (obj, fieldname, value)


class ListImpl:

    def __init__(self, receiver):
        self.obj = repr_arg(receiver)

    def ll_length(self):
        return "(length %s)" % (self.obj,)

    def ll_getitem_fast(self, index):
        index = repr_arg(index)
        return "(aref %s %s)" % (self.obj, index)

    def ll_setitem_fast(self, index, value):
        index = repr_arg(index)
        value = repr_arg(value)
        return "(setf (aref %s %s) %s)" % (self.obj, index, value)

    def _ll_resize(self, size):
        size = repr_arg(size)
        return "(adjust-array %s %s)" % (self.obj, size)


class GenCL:

    def __init__(self, entry_point, input_arg_types=[]):
        self.pendinggraphs = [entry_point]
        self.declarations = []

    def emitcode(self, public=True):
        lines = list(self.emit())
        declarations = "\n".join(self.declarations)
        code = "\n".join(lines)
        if declarations:
            return declarations + "\n" + code + "\n"
        else:
            return code + "\n"

    def emit(self):
        while self.pendinggraphs:
            graph = self.pendinggraphs.pop()
            for line in self.emit_defun(graph):
                yield line

    def emit_defun(self, fun):
        yield "(defun " + repr_fun_name(fun.name)
        arglist = fun.getargs()
        args = " ".join(map(repr_var, arglist))
        yield "(%s)" % (args,)
        yield "(prog"
        blocklist = list(fun.iterblocks())
        vardict = {}
        self.blockref = {}
        for block in blocklist:
            tag = len(self.blockref)
            self.blockref[block] = tag
            for var in block.getvariables():
                # In the future, we could assign type information here
                vardict[var] = None
        yield "("
        for var in vardict:
            if var in arglist:
                yield "(%s %s)" % (repr_var(var), repr_var(var))
            else:
                yield repr_var(var)
        yield ")"
        for block in blocklist:
            for line in self.emit_block(block):
                yield line
        yield "))"

    def emit_block(self, block):
        self.cur_block = block
        tag = self.blockref[block]
        yield "tag" + str(tag)
        for op in block.operations:
            emit_op = Op(self, op)
            for line in emit_op:
                yield line
        exits = block.exits
        if len(exits) == 1:
            for line in self.emit_link(exits[0]):
                yield line
        elif len(exits) > 1:
            # only works in the current special case
            if (len(exits) == 2 and
                exits[0].exitcase == False and
                exits[1].exitcase == True):
                yield "(if " + repr_arg(block.exitswitch)
                yield "(progn"
                for line in self.emit_link(exits[1]):
                    yield line
                yield ") ; else"
                yield "(progn"
                for line in self.emit_link(exits[0]):
                    yield line
                yield "))"
            else:
                # this is for the more general case.  The previous special case
                # shouldn't be needed but in Python 2.2 we can't tell apart
                # 0 vs nil  and  1 vs t  :-(
                for exit in exits[:-1]:
                    yield "(if (equalp " + repr_arg(block.exitswitch)
                    yield repr_const(exit.exitcase) + ')'
                    yield "(progn"
                    for line in self.emit_link(exit):
                        yield line
                    yield ")"
                yield "(progn ; else should be %s" % repr_const(exits[-1].exitcase)
                for line in self.emit_link(exits[-1]):
                    yield line
                yield ")" * len(exits)
        elif len(block.inputargs) == 2:    # exc_cls, exc_value
            exc_cls   = repr_var(block.inputargs[0])
            exc_value = repr_var(block.inputargs[1])
            yield "(something-like-throw-exception %s %s)" % (exc_cls, exc_value)
        else:
            retval = repr_var(block.inputargs[0])
            yield "(return %s )" % retval

    def format_jump(self, block):
        tag = self.blockref[block]
        return "(go tag" + str(tag) + ")"

    def emit_link(self, link):
        source = map(repr_arg, link.args)
        target = map(repr_var, link.target.inputargs)
        yield "(setf"
        couples = zip(source, target)
        for s, t in couples[:-1]:
            yield "%s %s" % (t, s)
        else:
            s, t = couples[-1]
            yield "%s %s)" % (t, s)
        yield self.format_jump(link.target)
