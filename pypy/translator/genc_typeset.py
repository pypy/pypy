from __future__ import generators
import re
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.annotation import model as annmodel
from pypy.translator import genc_op
from pypy.translator.typer import CannotConvert
from pypy.translator.genc_repr import R_VOID, R_INT, R_OBJECT, R_UNDEFINED
from pypy.translator.genc_repr import tuple_representation
from pypy.translator.genc_repr import constant_representation, CConstant
from pypy.translator.genc_repr import instance_representation, CInstance


class CTypeSet:
    "A (small) set of C types that typer.LLFunction can manipulate."

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
        self.conversion_cache = {}
        self.conversion_errors = {}
        self.lloperations = {'convert': self.conversion_cache}
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
                return constant_representation(var.const)
            if issubclass(var.knowntype, int):
                return R_INT
            if isinstance(var, annmodel.SomeImpossibleValue):
                return R_VOID
            if isinstance(var, annmodel.SomeTuple):
                items_r = [self.gethltype(s_item) for s_item in var.items]
                return tuple_representation(items_r)
            if isinstance(var, annmodel.SomeInstance):
                llclass = self.genc.llclasses[var.knowntype]
                return instance_representation(llclass)
            # fall-back
            return R_OBJECT
        if isinstance(var, UndefinedConstant):
            return R_UNDEFINED
        if isinstance(var, Constant):
            return constant_representation(var.value)
        raise TypeError, var

    def represent(self, hltype):
        return hltype.impl

    def getconversion(self, hltype1, hltype2):
        sig = hltype1, hltype2
        if sig in self.conversion_errors:
            raise CannotConvert   # shortcut
        try:
            return self.conversion_cache[sig]
        except KeyError:
            try:
                llopcls = hltype1.convert_to(hltype2, self)
                self.conversion_cache[sig] = llopcls
                return llopcls
            except CannotConvert:
                self.conversion_errors[sig] = True
                raise

    def typemismatch(self, opname, hltypes):
        # build operations on demand, e.g. if they take a variable number
        # of arguments or depend on a constant value (e.g. the class being
        # instantiated).
        try:
            extender = getattr(self, 'extend_' + opname)
        except AttributeError:
            return
        for newsig, newop in extender(hltypes):
            # record the new operation only if it has a lower cost than
            # an existing operation with the same signature
            llops = self.lloperations.setdefault(opname, {})
            if newsig not in llops or newop.cost < llops[newsig].cost:
                llops[newsig] = newop

    # ____________________________________________________________

    def extend_OP_NEWLIST(self, hltypes):
        # LoNewList can build a list of any length from PyObject* args.
        sig = (R_OBJECT,) * len(hltypes)
        yield sig, genc_op.LoNewList

    def extend_OP_NEWTUPLE(self, hltypes):
        # We can use LoCopy to virtually build a tuple because
        # the tuple representation 'rt' is just the collection of all the
        # representations for the input args.
        rt = tuple_representation(hltypes[:-1])
        sig = tuple(hltypes[:-1]) + (rt,)
        yield sig, genc_op.LoCopy

    def extend_OP_SIMPLE_CALL(self, hltypes):
        if not hltypes:
            return
        # We can call the function using PyObject_CallFunction(), if
        # it can be converted to PyObject*.
        sig = (R_OBJECT,) * len(hltypes)
        yield sig, genc_op.LoCallFunction
        # But not all variables holding pointers to function can nicely
        # be converted to PyObject*.  We might be calling a well-known
        # (constant) function:
        r = hltypes[0]
        if isinstance(r, CConstant):
            fn = r.value
            if not callable(fn):
                return
            # Calling another user-defined generated function
            if fn in self.genc.llfunctions:
                llfunc = self.genc.llfunctions[fn]
                sig = [r]
                for v in llfunc.graph.getargs():
                    sig.append(self.gethltype(v))
                hltype = self.gethltype(llfunc.graph.getreturnvar())
                sig.append(hltype)
                yield tuple(sig), genc_op.LoCallPyFunction.With(
                    llfunc = llfunc,
                    hlrettype = hltype,
                    )
            # Instantiating a user-defined class
            if fn in self.genc.llclasses:
                # XXX do __init__
                llclass = self.genc.llclasses[fn]
                r_result = instance_representation(llclass)
                sig = (r, r_result)   # r_result is the result of the op
                yield sig, genc_op.LoInstantiate.With(
                    llclass = self.genc.llclasses[fn],
                    )
            # Calling a built-in defined in genc.h, if we have a macro
            # CALL_funcname()
            opname = 'CALL_' + getattr(fn, '__name__', '?')
            if opname in self.lloperations:
                for sig, llopcls in self.lloperations[opname].items():
                    sig = (r,) + sig
                    yield sig, llopcls

    def extend_OP_ALLOC_INSTANCE(self, hltypes):
        # OP_ALLOC_INSTANCE is used by the constructor functions xxx_new()
        if not hltypes:
            return
        r = hltypes[0]
        if isinstance(r, CConstant):
            fn = r.value
            if not callable(fn):
                return
            if fn in self.genc.llclasses:
                llclass = self.genc.llclasses[fn]
                r_result = instance_representation(llclass)
                sig = (r, r_result)   # r_result is the result of the op
                yield sig, genc_op.LoAllocInstance.With(
                    llclass = llclass,
                    )

    def extend_OP_GETATTR(self, hltypes):
        if len(hltypes) != 3:
            return
        r_obj, r_attr, r_result = hltypes
        if isinstance(r_obj, CInstance) and isinstance(r_attr, CConstant):
            # record the OP_GETATTR operation for this field
            fld = r_obj.llclass.get_instance_field(r_attr.value)
            if fld is not None:
                sig = (r_obj, constant_representation(fld.name), fld.hltype)
                yield sig, genc_op.LoGetAttr.With(
                    fld     = fld,
                    )

    def extend_OP_SETATTR(self, hltypes):
        if len(hltypes) != 4:
            return
        r_obj, r_attr, r_value, r_voidresult = hltypes
        if isinstance(r_obj, CInstance):
            # record the OP_SETATTR operation for this field
            fld = r_obj.llclass.get_instance_field(r_attr.value)
            if fld is not None:
                sig = (r_obj, constant_representation(fld.name), fld.hltype,
                       R_VOID)
                yield sig, genc_op.LoSetAttr.With(
                    fld     = fld,
                    )

    # ____________________________________________________________

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
            cost     = 1 + typecodes.count('o'),   # rough cost estimate
            ))
