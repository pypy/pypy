import types

from pypy.tool.udir import udir
from pypy.translator.translator import graphof
from pypy.rpython.ootypesystem.ootype import List, Record, Instance, _static_meth, _meth, ROOT
from pypy.rpython.ootypesystem.rclass import OBJECT
from pypy.translator.cl.clrepr import repr_arg, repr_var, repr_const, repr_fun_name, repr_class_name


class Op:

    def __init__(self, gen, op):
        self.gen = gen
        self.op = op
        self.opname = op.opname
        self.args = op.args
        self.result = op.result

    def __iter__(self):
        method = getattr(self, "op_" + self.opname)
        result = repr_arg(self.result)
        args = map(repr_arg, self.args)
        for line in method(result, *args):
            yield line

    def nop(self, result, arg):
        yield "(setf %s %s)" % (result, arg)

    op_same_as = nop
    op_ooupcast = nop

    def make_binary_op(cl_op):
        def _(self, result, arg1, arg2):
            yield "(setf %s (%s %s %s))" % (result, cl_op, arg1, arg2)
        return _

    op_int_add = make_binary_op("+")
    op_int_mul = make_binary_op("*")
    op_int_eq = make_binary_op("=")
    op_int_gt = make_binary_op(">")
    op_int_ge = make_binary_op(">=")
    op_int_lt = make_binary_op("<")
    op_int_le = make_binary_op("<=")
    op_int_and = make_binary_op("logand")
    op_int_mod = make_binary_op("mod")
    op_int_sub = make_binary_op("-")
    op_float_sub = make_binary_op("-")
    op_float_truediv = make_binary_op("/")
    op_char_eq = make_binary_op("char=")
    op_char_le = make_binary_op("char<=")
    op_char_ne = make_binary_op("char/=")

    def op_cast_char_to_int(self, result, arg):
        yield "(setf %s (char-code %s))" % (result, arg)

    def op_cast_int_to_char(self, result, arg):
        yield "(setf %s (code-char %s))" % (result, arg)

    def op_cast_int_to_float(self, result, arg):
        yield "(setf %s (float %s))" % (result, arg)

    def op_bool_not(self, result, arg):
        yield "(setf %s (not %s))" % (result, arg)

    def op_int_is_true(self, result, arg):
        yield "(setf %s (not (zerop %s)))" % (result, arg)

    def op_direct_call(self, result, fun, *args):
        funobj = self.args[0].value
        self.gen.pendinggraphs.append(funobj)
        args = " ".join(args)
        yield "(setf %s (%s %s))" % (result, fun, args)

    def declare_struct(self, cls):
        # cls is Record
        name = "struct" + str(self.gen.structcount)
        field_declaration = cls._fields.keys()
        field_declaration = " ".join(field_declaration)
        struct_declaration = "(defstruct %s %s)" % (name, field_declaration)
        self.gen.declarations.append(struct_declaration)
        self.gen.structcount += 1
        return name

    def declare_class(self, cls):
        # cls is Instance
        name = repr_class_name(cls._name)
        field_declaration = ['('+field+')' for field in cls._fields]
        field_declaration = " ".join(field_declaration)
        if cls._superclass in (OBJECT, ROOT):
            class_declaration = "(defclass %s () (%s))" % (name, field_declaration)
        else:
            self.declare_class(cls._superclass)
            supername = repr_class_name(cls._superclass._name)
            class_declaration = "(defclass %s (%s) (%s))" % (name, supername, field_declaration)
        if class_declaration not in self.gen.declarations:
            self.gen.declarations.append(class_declaration)

    def op_new(self, result, clsname):
        cls = self.args[0].value
        if isinstance(cls, List):
            yield "(setf %s (make-array 0 :adjustable t))" % (result,)
        elif isinstance(cls, Record):
            clsname = self.declare_struct(cls)
            yield "(setf %s (make-%s))" % (result, clsname)
        elif isinstance(cls, Instance):
            self.declare_class(cls)
            yield "(setf %s (make-instance %s))" % (result, clsname)
        else:
            raise NotImplementedError()

    def op_instanceof(self, result, arg, clsname):
        yield "(setf %s (typep %s %s))" % (result, arg, clsname)

    def op_oosend(self, result, *ignore):
        method = self.args[0].value
        receiver = self.args[1]
        cls = receiver.concretetype
        args = self.args[2:]
        if isinstance(cls, List):
            impl = ListImpl(receiver)
            code = getattr(impl, method)(*args)
            yield "(setf %s %s)" % (result, code)
        elif isinstance(cls, Instance):
            methodobj = cls._methods[method]
            methodobj._method_name = method # XXX
            self.gen.pendinggraphs.append(methodobj)
            name = repr_fun_name(method)
            selfvar = repr_arg(receiver)
            args = map(repr_arg, args)
            args = " ".join(args)
            if args:
                yield "(setf %s (%s %s %s))" % (result, name, selfvar, args)
            else:
                yield "(setf %s (%s %s))" % (result, name, selfvar)

    def op_oogetfield(self, result, obj, _):
        fieldname = self.args[1].value
        yield "(setf %s (slot-value %s '%s))" % (result, obj, fieldname)

    def op_oosetfield(self, result, obj, _, value):
        fieldname = self.args[1].value
        if fieldname == "meta": # XXX
            raise StopIteration
        yield "(setf (slot-value %s '%s) %s)" % (obj, fieldname, value)

    def op_ooidentityhash(self, result, arg):
        yield "(setf %s (sxhash %s))" % (result, arg)

    def op_oononnull(self, result, arg):
        yield "(setf %s (not (null %s)))" % (result, arg)


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

    def __init__(self, context, funobj):
        self.context = context
        self.entry_point = funobj
        self.pendinggraphs = [funobj]
        self.declarations = []
        self.structcount = 0

    def emitfile(self):
        name = self.entry_point.func_name
        path = udir.join("%s.lisp" % (name,))
        code = self.emitcode()
        path.write(code)
        return str(path)

    def emitcode(self):
        lines = list(self.emit())
        declarations = "\n".join(self.declarations)
        code = "\n".join(lines)
        if declarations:
            return declarations + "\n" + code + "\n"
        else:
            return code + "\n"

    def emit(self):
        while self.pendinggraphs:
            obj = self.pendinggraphs.pop()
            if isinstance(obj, types.FunctionType):
                graph = graphof(self.context, obj)
                for line in self.emit_defun(graph):
                    yield line
            elif isinstance(obj, _static_meth):
                graph = obj.graph
                for line in self.emit_defun(graph):
                    yield line
            elif isinstance(obj, _meth):
                graph = obj.graph
                name = obj._method_name # XXX
                for line in self.emit_defmethod(graph, name):
                    yield line

    def emit_defun(self, fun):
        yield "(defun " + repr_fun_name(fun.name)
        arglist = fun.getargs()
        args = " ".join(map(repr_var, arglist))
        yield "(%s)" % (args,)
        for line in self.emit_body(fun, arglist):
            yield line

    def emit_defmethod(self, fun, name):
        yield "(defmethod %s" % (repr_fun_name(name))
        arglist = fun.getargs()
        selfvar = repr_var(arglist[0])
        clsname = repr_class_name(arglist[0].concretetype._name)
        args = " ".join(map(repr_var, arglist[1:]))
        if args:
            yield "((%s %s) %s)" % (selfvar, clsname, args)
        else:
            yield "((%s %s))" % (selfvar, clsname)
        for line in self.emit_body(fun, arglist):
            yield line

    def emit_body(self, fun, arglist):
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
        varnames = []
        for var in vardict:
            varname = repr_var(var)
            if var in arglist:
                varnames.append("(%s %s)" % (varname, varname))
            else:
                varnames.append(varname)
        varnames = " ".join(varnames)
        yield "(%s)" % (varnames,)
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
            yield "(return %s)" % retval

    def format_jump(self, block):
        tag = self.blockref[block]
        return "(go tag" + str(tag) + ")"

    def emit_link(self, link):
        source = map(repr_arg, link.args)
        target = map(repr_var, link.target.inputargs)
        couples = [ "%s %s" % (t, s) for (s, t) in zip(source, target)]
        couples = " ".join(couples)
        yield "(setf %s)" % (couples,)
        yield self.format_jump(link.target)
