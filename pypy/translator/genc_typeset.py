import re, types, __builtin__
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.annotation import model as annmodel
from pypy.translator.typer import LLConst
from pypy.translator import genc_op


class CRepr:
    "A possible representation of a flow-graph variable as C-level variables."

    def __init__(self, impl, parse_code=None, name=None):
        self.impl = impl   # list [(C type, prefix for variable name)]
        self.parse_code = parse_code  # character(s) for PyArg_ParseTuple()
        self.name = name or '<C %s>' % ' + '.join(self.impl)

    def __repr__(self):
        return self.name


class CTypeSet:
    "A (small) set of C types that typer.LLFunction can manipulate."

    R_VOID     = CRepr([])
    R_INT      = CRepr(['int'],       parse_code='i')
    R_OBJECT   = CRepr(['PyObject*'], parse_code='O')
    #R_DONTCARE = CRepr([])   # for uninitialized variables

    REPR_BY_CODE = {
        'v': R_VOID,
        'i': R_INT,
        'o': R_OBJECT,
        }

    rawoperations = {
        'goto'   : genc_op.LoGoto,
        'move'   : genc_op.LoMove,
        'copy'   : genc_op.LoCopy,
        'incref' : genc_op.LoIncref,
        'decref' : genc_op.LoDecref,
        'xdecref': genc_op.LoXDecref,
        'comment': genc_op.LoComment,
        'return' : genc_op.LoReturn,
        }

    def __init__(self, genc, bindings):
        self.genc = genc
        self.bindings = bindings
        self.r_constants = {}
        self.r_tuples = {}
        self.lloperations = {'convert': {}}
        self.parse_operation_templates()

    # __________ methods required by LLFunction __________
    #
    # Here, we assume that every high-level type has a canonical representation
    # so a high-level type is just a CRepr.

    def gethltype(self, var):
        if isinstance(var, Variable):
            var = self.bindings.get(var) or annmodel.SomeObject()
        if isinstance(var, annmodel.SomeObject):
            if var.is_constant():
                return self.constant_representation(var.const)
            if issubclass(var.knowntype, int):
                return self.R_INT
            if isinstance(var, annmodel.SomeImpossibleValue):
                return self.R_VOID
            if isinstance(var, annmodel.SomeTuple):
                items_r = [self.gethltype(s_item) for s_item in var.items]
                return self.tuple_representation(items_r)
            # fall-back
            return self.R_OBJECT
        #if isinstance(var, UndefinedConstant):
        #    return self.R_DONTCARE
        if isinstance(var, Constant):
            return self.constant_representation(var.value)
        raise TypeError, var

    def represent(self, hltype):
        return hltype.impl

    def typingerror(self, opname, hltypes):
        # build operations with a variable number of arguments on demand
        if opname == 'OP_NEWLIST':
            opnewlist = self.lloperations.setdefault('OP_NEWLIST', {})
            sig = (self.R_OBJECT,) * len(hltypes)
            if sig in opnewlist:
                return False
            opnewlist[sig] = genc_op.LoNewList
            return True   # retry
        if opname == 'OP_NEWTUPLE':
            opnewtuple = self.lloperations.setdefault('OP_NEWTUPLE', {})
            rt = self.tuple_representation(hltypes[:-1])
            sig = tuple(hltypes[:-1]) + (rt,)
            if sig in opnewtuple:
                return False
            opnewtuple[sig] = genc_op.LoCopy
            # Note that we can use LoCopy to virtually build a tuple because
            # the tuple representation 'rt' is just the collection of all the
            # representations for the input args.
            return True   # retry
        if opname == 'OP_SIMPLE_CALL' and hltypes:
            opsimplecall = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
            sig = (self.R_OBJECT,) * len(hltypes)
            if sig in opsimplecall:
                return False
            opsimplecall[sig] = genc_op.LoCallFunction
            return True   # retry
        return False

    # ____________________________________________________________

    def constant_representation(self, value):
        key = type(value), value   # to avoid mixing for example 0 and 0.0
        try:
            return self.r_constants[key]
        except KeyError:
            if isinstance(value, tuple):
                # tuples have their own representation and
                # don't need a fully constant representation
                items_r = [self.constant_representation(x) for x in value]
                return self.tuple_representation(items_r)
            # a constant doesn't need any C variable to be encoded
            r = self.r_constants[key] = CRepr([], name='<const %r>' % (value,))
            r.const = value

            # but to convert it to something more general like an int or
            # a PyObject* we need to revive its value, which is done by
            # new conversion operations that we define now
            if isinstance(value, int):
                # can convert the constant to a PyObject*
                if value >= 0:
                    name = 'g_IntObj_%d' % value
                else:
                    name = 'g_IntObj_minus%d' % abs(value)
                self.can_convert_to_pyobj(r, 'PyInt_FromLong(%d)' % value,
                                          name)
                # can convert the constant to a C int
                self.register_conv(r, self.R_INT, genc_op.LoKnownAnswer.With(
                    known_answer = [LLConst(self.R_INT, '%d' % value)],
                    ))
            elif isinstance(value, str):
                # can convert the constant to a PyObject*
                self.can_convert_to_pyobj(r,
                    'PyString_FromStringAndSize(%s, %d)' % (c_str(value),
                                                            len(value)),
                    'g_StrObj_%s' % manglestr(value))
            elif value is None:
                # can convert the constant to Py_None
                self.can_convert_to_pyobj(r, None, 'Py_None')
            elif callable(value) and value in self.genc.llfunctions:
                # another Python function: can be called with OP_SIMPLE_CALL
                llfunc = self.genc.llfunctions[value]
                ops = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
                sig = [r]
                for v in llfunc.graph.getargs():
                    sig.append(self.gethltype(v))
                hltype = self.gethltype(llfunc.graph.getreturnvar())
                sig.append(hltype)
                ops[tuple(sig)] = genc_op.LoCallPyFunction.With(
                    llfunc = llfunc,
                    hlrettype = hltype,
                    )
            elif (isinstance(value, types.BuiltinFunctionType) and
                  value is getattr(__builtin__, value.__name__, None)):
                # a function from __builtin__: can convert to PyObject*
                self.can_convert_to_pyobj(r,
                    'PyMapping_GetItemString(PyEval_GetBuiltins(), %s)' % (
                    c_str(value.__name__)),
                    'g_Builtin_%s' % manglestr(value.__name__))
                # if the function is defined in genc.h, import its definition
                # by copying the operation CALL_xxx to OP_SIMPLE_CALL with
                # a first argument which is the constant function xxx.
                opname = 'CALL_' + value.__name__
                if opname in self.lloperations:
                    ops = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
                    for sig, llopcls in self.lloperations[opname].items():
                        sig = (r,) + sig
                        ops[sig] = llopcls
            elif (isinstance(value, (type, types.ClassType)) and
                  value in self.genc.llclasses):
                # a user-defined class
                ops = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
                # XXX do __init__
                sig = (r, self.R_OBJECT)
                ops[sig] = genc_op.LoInstantiate.With(
                    llclass = self.genc.llclasses[value],
                    )
                # OP_ALLOC_INSTANCE used by the constructor function xxx_new()
                ops = self.lloperations.setdefault('OP_ALLOC_INSTANCE', {})
                sig = (r, self.R_OBJECT)
                ops[sig] = genc_op.LoAllocInstance.With(
                    llclass = self.genc.llclasses[value],
                    )
            else:
                print "// XXX not implemented: constant", key
            return r

    def can_convert_to_pyobj(self, r, initexpr, globalname):
        self.register_conv(r, self.R_OBJECT, genc_op.LoKnownAnswer.With(
            known_answer = [LLConst('PyObject*', globalname, initexpr,
                                    to_declare = bool(initexpr))],
            ))

    def tuple_representation(self, items_r):
        # a tuple is implemented by several C variables or fields
        # instead of a single struct at the C level.
        items_r = tuple(items_r)
        try:
            return self.r_tuples[items_r]
        except KeyError:
            impl = []
            for r in items_r:
                impl += r.impl
            name = '<(%s)>' % ', '.join([str(r) for r in items_r])
            rt = CRepr(impl, name=name)
            self.r_tuples[items_r] = rt

            # we can convert any item in the tuple to obtain another tuple
            # representation.
            conv = self.lloperations['convert']
            for i in range(len(items_r)):
                r = items_r[i]
                for r_from, r_to in conv.keys():
                    if r_from == r:
                        target_r = list(items_r)
                        target_r[i] = r_to
                        rt_2 = self.tuple_representation(target_r)
                        self.register_conv(rt, rt_2,
                                           genc_op.LoConvertTupleItem.With(
                            source_r = items_r,
                            target_r = target_r,
                            index    = i,
                            ))

            # a tuple containing only PyObject* can easily be converted to
            # a PyTupleObject.  (For other kinds of tuple the conversion is
            # indirect: all items can probably be converted, one by one, to
            # PyObject*, and the conversions will be chained automatically.)
            if items_r == (self.R_OBJECT,) * len(items_r):
                self.register_conv(rt, self.R_OBJECT, genc_op.LoNewTuple)

            return rt

    def parse_operation_templates(self):
        # parse the genc.h header to figure out which macros are implemented
        codes = ''.join(self.REPR_BY_CODE.keys())
        pattern = r"#define ([A-Za-z_][0-9A-Za-z_]*)_([%s]*)[(](.*?)[)]" % codes
        rexp = re.compile(pattern)
        for line in self.genc.C_HEADER.split('\n'):
            match = rexp.match(line)
            if match:
                self.register_operation_template(*match.groups())

    def register_operation_template(self, opname, typecodes, formalargs):
        llname = '%s_%s' % (opname, typecodes)
        sig = tuple([self.REPR_BY_CODE[code] for code in typecodes])
        can_fail = formalargs.replace(' ','').endswith(',err')
        ops = self.lloperations.setdefault(opname, {})
        assert sig not in ops, llname
        ops.setdefault(sig, genc_op.LoStandardOperation.With(
            can_fail = can_fail,
            llname   = llname,
            ))

    def register_conv(self, r_from, r_to, convopcls):
        conv = self.lloperations['convert']
        if r_from == r_to:
            return
        prevconvopcls = conv.get((r_from, r_to))
        if prevconvopcls is not None:
            if convert_length(prevconvopcls) > convert_length(convopcls):
                # only replace a conversion with another if the previous one
                # was a longer chain of conversions
                del conv[r_from, r_to]
            else:
                return
        #print 'conv: %s\t->\t%s' % (r_from, r_to)
        convitems = conv.items()   # not iteritems()!
        conv[r_from, r_to] = convopcls
        # chain the conversion with any other possible conversion
        for (r_from_2, r_to_2), convopcls_2 in convitems:
            if r_to == r_from_2:
                self.register_conv(r_from, r_to_2, genc_op.LoConvertChain.With(
                    r_from         = r_from,
                    r_middle       = r_to,
                    r_to           = r_to_2,
                    convert_length = convert_length(convopcls) +
                                     convert_length(convopcls_2),
                    ))
            if r_to_2 == r_from:
                self.register_conv(r_from_2, r_to, genc_op.LoConvertChain.With(
                    r_from         = r_from_2,
                    r_middle       = r_to_2,
                    r_to           = r_to,
                    convert_length = convert_length(convopcls_2) +
                                     convert_length(convopcls),
                    ))

def convert_length(convopcls):
    if issubclass(convopcls, genc_op.LoConvertChain):
        return convopcls.convert_length
    else:
        return 1

def c_str(s):
    "Return the C expression for the string 's'."
    s = repr(s)
    if s.startswith("'"):
        s = '"' + s[1:-1].replace('"', r'\"') + '"'
    return s

def manglestr(s):
    "Return an identifier name unique for the string 's'."
    l = []
    for c in s:
        if not ('a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9'):
            if c == '_':
                c = '__'
            else:
                c = '_%02x' % ord(c)
        l.append(c)
    return ''.join(l)
