import re, types, __builtin__
from pypy.objspace.flow.model import Variable, Constant
from pypy.annotation import model as annmodel
from pypy.translator.typer import LLConst


class CRepr:
    "A possible representation of a flow-graph variable as C-level variables."

    def __init__(self, impl, err_check=None, parse_code=None):
        self.impl = impl   # list [(C type, prefix for variable name)]
        self.err_check = err_check  # condition to check for error return value
        self.parse_code = parse_code  # character(s) for PyArg_ParseTuple()

    def __repr__(self):
        if hasattr(self, 'const'):
            return '<C:= %r>' % (self.const,)
        else:
            return '<C: %s>' % ' + '.join(self.impl)


class CTypeSet:
    "A (small) set of C types that typer.LLFunction can manipulate."

    R_VOID   = CRepr([])
    R_INT    = CRepr(['int'],       err_check='< 0',     parse_code='i')
    R_OBJECT = CRepr(['PyObject*'], err_check='== NULL', parse_code='O')

    REPR_BY_CODE = {
        'v': R_VOID,
        'i': R_INT,
        'o': R_OBJECT,
        }

    def __init__(self, genc, bindings):
        self.genc = genc
        self.bindings = bindings
        self.r_constants = {}
        self.r_tuples = {}
        self.lloperations = {'convert': {}, 'release': {}}
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
            def writer(*stuff):
                content = stuff[:-2]
                result = stuff[-2]
                err = stuff[-1]
                ls = ['if (!(%s = PyList_New(%d))) goto %s;' % (
                    result, len(content), err)]
                for i in range(len(content)):
                    ls.append('PyList_SET_ITEM(%s, %d, %s); Py_INCREF(%s);' % (
                        result, i, content[i], content[i]))
                return '\n'.join(ls)
            opnewlist[sig] = writer, True
            return True   # retry
        if opname == 'OP_NEWTUPLE':
            opnewtuple = self.lloperations.setdefault('OP_NEWTUPLE', {})
            rt = self.tuple_representation(hltypes[:-1])
            sig = tuple(hltypes[:-1]) + (rt,)
            if sig in opnewtuple:
                return False
            opnewtuple[sig] = 'copy', False
            return True   # retry
        if opname == 'OP_SIMPLE_CALL' and hltypes:
            opsimplecall = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
            sig = (self.R_OBJECT,) * len(hltypes)
            if sig in opsimplecall:
                return False
            def writer(func, *stuff):
                args = stuff[:-2]
                result = stuff[-2]
                err = stuff[-1]
                format = '"' + 'O' * len(args) + '"'
                args = (func, format) + args
                return ('if (!(%s = PyObject_CallFunction(%s)))'
                        ' goto %s;' % (result, ', '.join(args), err))
            opsimplecall[sig] = writer, True
            return True   # retry
        return False

    def knownanswer(self, llname):
        return getattr(llname, 'known_answer', None)

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
            r = self.r_constants[key] = CRepr([])
            r.const = value
            # returning a constant
            def writer():
                return 'return 0;'
            self.lloperations['return'][r,] = writer, False
            def writer():
                return 'return -1;'
            self.lloperations['returnerr'][r,] = writer, False
            
            # but to convert it to something more general like an int or
            # a PyObject* we need to revive its value, which is done by
            # new conversion operations that we define now
            conv = self.lloperations['convert']
            if isinstance(value, int):
                # can convert the constant to a C int
                def writer(z):
                    return '%s = %d;' % (z, value)
                conv[r, self.R_INT] = writer, False
                writer.known_answer = [LLConst(self.R_INT, '%d' % value)]
                # can convert the constant to a PyObject*
                if value >= 0:
                    name = 'g_IntObj_%d' % value
                else:
                    name = 'g_IntObj_minus%d' % abs(value)
                self.can_convert_to_pyobj(r, 'PyInt_FromLong(%d)' % value,
                                          name)
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
                if len(hltype.impl) == 0:   # no return value
                    def writer(*stuff):
                        args = stuff[:-1]
                        err = stuff[-1]
                        return 'if (%s(%s) < 0) goto %s;' % (
                            llfunc.name, ', '.join(args), err)
                elif len(hltype.impl) == 1:  # one LLVar for the return value
                    def writer(*stuff):
                        args = stuff[:-2]
                        result = stuff[-2]
                        err = stuff[-1]
                        return ('if ((%s = %s(%s)) %s) goto %s;' % (
                            result, llfunc.name, ', '.join(args),
                            hltype.err_check, err))
                else:
                    XXX("to do")
                ops[tuple(sig)] = writer, True
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
                    for sig, ll in self.lloperations[opname].items():
                        sig = (r,) + sig
                        ops[sig] = ll
            elif (isinstance(value, (type, types.ClassType)) and
                  value in self.genc.llclasses):
                # a user-defined class
                ops = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
                # XXX do __init__
                sig = (r, self.R_OBJECT)
                def writer(res, err):
                    return 'INSTANTIATE(%s, %s, %s)' % (
                        self.genc.llclasses[value].name, res, err)
                ops[sig] = writer, True
                # OP_ALLOC_INSTANCE used by the constructor function xxx_new()
                ops = self.lloperations.setdefault('OP_ALLOC_INSTANCE', {})
                sig = (r, self.R_OBJECT)
                def writer(res, err):
                    return 'ALLOC_INSTANCE(%s, %s, %s)' % (
                        self.genc.llclasses[value].name, res, err)
                ops[sig] = writer, True
            else:
                print "// XXX not implemented: constant", key
            return r

    def can_convert_to_pyobj(self, r, initexpr, globalname):
        conv = self.lloperations['convert']
        def writer(z):
            return '%s = %s; Py_INCREF(%s);' % (z, globalname, z)
        conv[r, self.R_OBJECT] = writer, False
        llconst = LLConst('PyObject*', globalname, initexpr,
                          to_declare = bool(initexpr))
        writer.known_answer = [llconst]

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
            rt = CRepr(impl)
            if items_r:
                rt.err_check = items_r[0].err_check
            self.r_tuples[items_r] = rt
            # can convert the tuple to a PyTupleObject only if each item can be
            conv = self.lloperations['convert']
            also_using = []
            for r in items_r:
                if r == self.R_OBJECT:
                    continue
                if (r, self.R_OBJECT) not in conv:
                    break
                llname, can_fail = conv[r, self.R_OBJECT]
                also_using.append(llname)
            else:
                def writer(*args):
                    content = args[:-2]
                    result = args[-2]
                    err = args[-1]
                    ls = ['{',
                          'PyObject* o;',
                          'if (!(%s = PyTuple_New(%d))) goto %s;' % (
                                result, len(items_r), err)]
                    j = 0
                    for i in range(len(items_r)):
                        r = items_r[i]
                        if r == self.R_OBJECT:
                            o = content[j]
                            j = j+1
                            ls.append('Py_INCREF(%s);' % o)
                        else:
                            o = 'o'
                            llname, can_fail = conv[r, self.R_OBJECT]
                            k = len(r.impl)
                            args = content[j:j+k] + (o,)
                            j = j+k
                            if can_fail:
                                args += (err,)
                            ls.append(llname(*args))
                        ls.append('PyTuple_SET_ITEM(%s, %d, %s);' %
                                  (result, i, o))
                    return '\n'.join(ls).replace('\n', '\n\t') + '\n}'
                writer.also_using = also_using
                conv[rt, self.R_OBJECT] = writer, True
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
        # the operation's low-level name is a callable that will
        # produce the correct macro call
        def writer(*args):
            return llname + '(' + ', '.join(args) + ')'
        ops.setdefault(sig, (writer, can_fail))

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

def consts_used(writer):
    "Enumerate the global constants that a writer function uses."
    result = getattr(writer, 'known_answer', [])
    if hasattr(writer, 'also_using'):
        result = list(result)
        for w in writer.also_using:
            result += consts_used(w)
    return result
