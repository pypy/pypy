from __future__ import generators
import re
from pypy.objspace.flow.model import Variable, Constant, UndefinedConstant
from pypy.annotation import model as annmodel
from pypy.translator import genc_op
from pypy.translator.typer import CannotConvert, TypingError, LLConst
from pypy.translator.genc_repr import R_VOID, R_INT, R_OBJECT, R_UNDEFINED
from pypy.translator.genc_repr import R_INSTANCE
from pypy.translator.genc_repr import tuple_representation
from pypy.translator.genc_repr import constant_representation, CConstant
from pypy.translator.genc_repr import instance_representation, CInstance
from pypy.translator.genc_repr import function_representation, CFunction
from pypy.translator.genc_repr import CConstantFunction
from pypy.translator.genc_repr import method_representation, CMethod
from pypy.translator.genc_repr import list_representation, CList


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
        self.lloperations = {'CONVERT': self.conversion_cache}
        self.parse_operation_templates()

    # __________ methods required by LLFunction __________
    #
    # Here, we assume that every high-level type has a canonical representation
    # so a high-level type is just a CRepr.

    def gethltype(self, var, unbound=False):
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
            if isinstance(var, annmodel.SomeFunction):
                func_sig = self.regroup_func_sig(var.funcs)
                return function_representation(func_sig)
            if isinstance(var, annmodel.SomeMethod):
                r_func = self.gethltype(annmodel.SomeFunction(var.meths))
                if unbound:
                    return r_func
                else:
                    return method_representation(r_func)
            if 0: # still working on it -- isinstance(var, annmodel.SomeList):
                r_item = self.gethltype(var.s_item)
                typename = self.genc.declare_list(r_item.impl)
                r = list_representation(r_item)
                r.typename = typename
                return r
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
            raise CannotConvert(hltype1, hltype2)   # shortcut
        try:
            return self.conversion_cache[sig]
        except KeyError:
            try:
                llopcls = hltype1.convert_to(hltype2, self)
                self.conversion_cache[sig] = llopcls
                return llopcls
            except CannotConvert, e:
                self.conversion_errors[sig] = True
                if not e.args:
                    e.args = hltype1, hltype2
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

    def getfunctionsig(self, llfunc):
        "Get the high-level header (argument types and result) for a function."
        # XXX messy! we allow different CInstances to appear as function
        #     arguments by replacing them with the generic R_INSTANCE.
        #     This is not too clean, but it might be unavoidable, because
        #     the whole implementation relies on this "coincidence" that
        #     pointers to objects of different classes are interchangeable.
        result = []
        for v in llfunc.graph.getargs() + [llfunc.graph.getreturnvar()]:
            r = self.gethltype(v)
            if isinstance(r, CInstance):
                r = R_INSTANCE
            result.append(r)
        return result

    def regroup_func_sig(self, funcs):
        # find a common signature for the given functions
        signatures = []
        for func in funcs:
            llfunc = self.genc.llfunctions[func]
            signatures.append(self.getfunctionsig(llfunc))
        # XXX we expect the functions to have exactly the same signature
        #     but this is currently not enforced by the annotator.
        result = signatures[0]
        for test in signatures[1:]:
            if test != result:
                raise TypingError(test, result)
        return result

    # ____________________________________________________________

    def extend_OP_NEWLIST(self, hltypes):
        if not hltypes:
            return
        # LoNewList can build a list of any length from PyObject* args.
        sig = (R_OBJECT,) * len(hltypes)
        yield sig, genc_op.LoNewList

        # LoNewArray can build an array from items of the correct type.
        r = hltypes[-1]
        if isinstance(r, CList):
            sig = (r.r_item,) * (len(hltypes)-1) + (r,)
            yield sig, genc_op.LoNewArray.With(
                typename = r.typename,
                lltypes  = r.r_item.impl,
                )

    def extend_OP_ALLOC_AND_SET(self, hltypes):
        if len(hltypes) != 3:
            return
        # we have LoAllocAndSetArray
        r_length, r_input, r = hltypes
        if isinstance(r, CList):
            sig = (R_INT, r.r_item, r)
            yield sig, genc_op.LoAllocAndSetArray.With(
                typename = r.typename,
                lltypes  = r.r_item.impl,
                )

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

        r = hltypes[0]
        if (isinstance(r, CConstantFunction) and
            r.value in self.genc.llfunctions):
            # a constant function can be converted to a function pointer,
            # so we fall back to the latter case
            llfunc = self.genc.llfunctions[r.value]
            r = function_representation(self.getfunctionsig(llfunc))

        if isinstance(r, CFunction):
            # a function pointer (the pointer is a C pointer, but points
            # to a C function generated from a user-defined Python function).
            sig = (r,) + tuple(r.header_r)
            yield sig, genc_op.LoCallPyFunction.With(
                hlrettype = sig[-1],
                )

        if isinstance(r, CMethod):
            # first consider how we could call the underlying function
            # with an extra R_INSTANCE first argument
            hltypes2 = (r.r_func, R_INSTANCE) + hltypes[1:]
            self.typemismatch('OP_SIMPLE_CALL', hltypes2)
            # then lift all OP_SIMPLE_CALLs to method calls
            opsimplecall = self.lloperations.setdefault('OP_SIMPLE_CALL', {})
            for sig, opcls in opsimplecall.items():
                if sig[1:2] == (R_INSTANCE,):
                    r = method_representation(sig[0])
                    sig2 = (r,) + sig[2:]
                    yield sig2, opcls
            # Note that we are reusing the same opcls.  Indeed, both the
            # original 'sig' and the modified one expand to the same list
            # of LLVars, so opcls cannot tell the difference:
            #
            # sig =    r.r_func     R_INSTANCE      ...
            #          /-----\    /------------\
            # LLVars:  funcptr,   PyObject* self,  arguments..., result
            #          \-----------------------/
            # sig2 =               r                ...

        if isinstance(r, CConstant):
            # maybe it is a well-known constant non-user-defined function
            fn = r.value
            if not callable(fn):
                return
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
        if not isinstance(r_attr, CConstant):
            return
        if isinstance(r_obj, CInstance):
            # record the OP_GETATTR operation for this field
            fld = (r_obj.llclass.get_instance_field(r_attr.value) or
                   r_obj.llclass.get_class_field(r_attr.value))
            if fld is None:
                return
            sig = (r_obj, r_attr, fld.hltype)
            # special case: reading a function out of a class attribute
            # produces a bound method
            if fld.is_class_attr:
                r = sig[-1]
                if isinstance(r, (CFunction, CConstantFunction)):
                    r_method = method_representation(r)
                    sig = (r_obj, r_attr, r_method)
                    yield sig, genc_op.LoGetAttrMethod.With(
                        fld = fld,
                        )
                    return
            # common case
            yield sig, genc_op.LoGetAttr.With(
                fld = fld,
                )

    def extend_OP_SETATTR(self, hltypes):
        if len(hltypes) != 4:
            return
        r_obj, r_attr, r_value, r_voidresult = hltypes
        if not isinstance(r_attr, CConstant):
            return
        if isinstance(r_obj, CInstance):
            # record the OP_SETATTR operation for this field
            fld = r_obj.llclass.get_instance_field(r_attr.value)
            if fld is not None:
                sig = (r_obj, r_attr, fld.hltype, R_VOID)
                yield sig, genc_op.LoSetAttr.With(
                    fld     = fld,
                    llclass = r_obj.llclass,
                    )

    def extend_OP_INITCLASSATTR(self, hltypes):
        # only to initialize class attributes
        if len(hltypes) != 4:
            return
        r_obj, r_attr, r_value, r_voidresult = hltypes
        if isinstance(r_attr, CConstant) and isinstance(r_obj, CConstant):
            cls = r_obj.value
            if cls in self.genc.llclasses:
                llclass = self.genc.llclasses[cls]
                fld = llclass.get_class_field(r_attr.value)
                if fld is not None:
                    sig = (r_obj, r_attr, fld.hltype, R_VOID)
                    yield sig, genc_op.LoInitClassAttr.With(
                        fld     = fld,
                        llclass = llclass,
                        )

    def extend_OP_GETITEM(self, hltypes):
        if len(hltypes) != 3:
            return
        r, r_index, r_result = hltypes
        # reading from a CList
        if isinstance(r, CList):
            sig = (r, R_INT, r.r_item)
            yield sig, genc_op.LoGetArrayItem.With(
                typename = r.typename,
                lltypes  = r.r_item.impl,
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
