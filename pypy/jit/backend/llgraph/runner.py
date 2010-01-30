"""
Minimal-API wrapper around the llinterpreter to run operations.
"""

import sys
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.objectmodel import we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.llinterp import LLInterpreter
from pypy.jit.metainterp import history
from pypy.jit.metainterp.history import REF, INT, FLOAT
from pypy.jit.metainterp.warmstate import unwrap
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend import model
from pypy.jit.backend.llgraph import llimpl, symbolic
from pypy.jit.metainterp.typesystem import llhelper, oohelper

class MiniStats:
    pass


class Descr(history.AbstractDescr):

    def __init__(self, ofs, typeinfo, extrainfo=None, name=None):
        self.ofs = ofs
        self.typeinfo = typeinfo
        self.extrainfo = extrainfo
        self.name = name

    def get_extra_info(self):
        return self.extrainfo

    def sort_key(self):
        """Returns an integer that can be used as a key when sorting the
        field descrs of a single structure.  The property that this
        number has is simply that two different field descrs of the same
        structure give different numbers."""
        return self.ofs

    def is_pointer_field(self):
        return self.typeinfo == REF

    def is_float_field(self):
        return self.typeinfo == FLOAT

    def is_array_of_pointers(self):
        return self.typeinfo == REF

    def is_array_of_floats(self):
        return self.typeinfo == FLOAT

    def __lt__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __le__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __gt__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __ge__(self, other):
        raise TypeError("cannot use comparison on Descrs")

    def __repr__(self):
        args = [repr(self.ofs), repr(self.typeinfo)]
        if self.name is not None:
            args.append(repr(self.name))
        if self.extrainfo is not None:
            args.append('E')
        return '<Descr %r>' % (', '.join(args),)


history.TreeLoop._compiled_version = lltype.nullptr(llimpl.COMPILEDLOOP.TO)


class BaseCPU(model.AbstractCPU):
    supports_floats = True

    def __init__(self, rtyper, stats=None, opts=None,
                 translate_support_code=False,
                 annmixlevel=None, gcdescr=None):
        assert type(opts) is not bool
        model.AbstractCPU.__init__(self)
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.stats = stats or MiniStats()
        self.stats.exec_counters = {}
        self.stats.exec_jumps = 0
        self.stats.exec_conditional_jumps = 0
        self.memo_cast = llimpl.new_memo_cast()
        llimpl._stats = self.stats
        llimpl._llinterp = LLInterpreter(self.rtyper)
        self._future_values = []
        self._descrs = {}

    def _freeze_(self):
        assert self.translate_support_code
        return False

    def getdescr(self, ofs, typeinfo='?', extrainfo=None, name=None):
        key = (ofs, typeinfo, extrainfo, name)
        try:
            return self._descrs[key]
        except KeyError:
            descr = Descr(ofs, typeinfo, extrainfo, name)
            self._descrs[key] = descr
            return descr

    def set_class_sizes(self, class_sizes):
        self.class_sizes = class_sizes
        for vtable, size in class_sizes.items():
            if not self.is_oo:
                size = size.ofs
            llimpl.set_class_size(self.memo_cast, vtable, size)

    def compile_bridge(self, faildescr, inputargs, operations):
        c = llimpl.compile_start()
        self._compile_loop_or_bridge(c, inputargs, operations)
        old, oldindex = faildescr._compiled_fail
        llimpl.compile_redirect_fail(old, oldindex, c)

    def compile_loop(self, inputargs, operations, loopdescr):
        """In a real assembler backend, this should assemble the given
        list of operations.  Here we just generate a similar CompiledLoop
        instance.  The code here is RPython, whereas the code in llimpl
        is not.
        """
        c = llimpl.compile_start()
        loopdescr._llgraph_compiled_version = c
        self._compile_loop_or_bridge(c, inputargs, operations)

    def _compile_loop_or_bridge(self, c, inputargs, operations):
        var2index = {}
        for box in inputargs:
            if isinstance(box, history.BoxInt):
                var2index[box] = llimpl.compile_start_int_var(c)
            elif isinstance(box, self.ts.BoxRef):
                TYPE = self.ts.BASETYPE
                var2index[box] = llimpl.compile_start_ref_var(c, TYPE)
            elif isinstance(box, history.BoxFloat):
                var2index[box] = llimpl.compile_start_float_var(c)
            else:
                raise Exception("box is: %r" % (box,))
        self._compile_operations(c, operations, var2index)
        return c

    def _compile_operations(self, c, operations, var2index):
        for op in operations:
            llimpl.compile_add(c, op.opnum)
            descr = op.descr
            if isinstance(descr, Descr):
                llimpl.compile_add_descr(c, descr.ofs, descr.typeinfo)
            if isinstance(descr, history.LoopToken) and op.opnum != rop.JUMP:
                llimpl.compile_add_loop_token(c, descr)
            if self.is_oo and isinstance(descr, (OODescr, MethDescr)):
                # hack hack, not rpython
                c._obj.externalobj.operations[-1].descr = descr
            for x in op.args:
                if isinstance(x, history.Box):
                    llimpl.compile_add_var(c, var2index[x])
                elif isinstance(x, history.ConstInt):
                    llimpl.compile_add_int_const(c, x.value)
                elif isinstance(x, self.ts.ConstRef):
                    llimpl.compile_add_ref_const(c, x.value, self.ts.BASETYPE)
                elif isinstance(x, history.ConstAddr):
                    llimpl.compile_add_int_const(c, x.getint())
                elif isinstance(x, history.ConstFloat):
                    llimpl.compile_add_float_const(c, x.value)
                else:
                    raise Exception("%s args contain: %r" % (op.getopname(),
                                                             x))
            if op.is_guard():
                faildescr = op.descr
                assert isinstance(faildescr, history.AbstractFailDescr)
                faildescr._fail_args_types = []
                for box in op.fail_args:
                    if box is None:
                        type = history.HOLE
                    else:
                        type = box.type
                    faildescr._fail_args_types.append(type)
                fail_index = self.get_fail_descr_number(faildescr)
                index = llimpl.compile_add_fail(c, fail_index)
                faildescr._compiled_fail = c, index
                for box in op.fail_args:
                    if box is not None:
                        llimpl.compile_add_fail_arg(c, var2index[box])
                    else:
                        llimpl.compile_add_fail_arg(c, -1)
            x = op.result
            if x is not None:
                if isinstance(x, history.BoxInt):
                    var2index[x] = llimpl.compile_add_int_result(c)
                elif isinstance(x, self.ts.BoxRef):
                    var2index[x] = llimpl.compile_add_ref_result(c, self.ts.BASETYPE)
                elif isinstance(x, history.BoxFloat):
                    var2index[x] = llimpl.compile_add_float_result(c)
                else:
                    raise Exception("%s.result contain: %r" % (op.getopname(),
                                                               x))
        op = operations[-1]
        assert op.is_final()
        if op.opnum == rop.JUMP:
            targettoken = op.descr
            assert isinstance(targettoken, history.LoopToken)
            compiled_version = targettoken._llgraph_compiled_version
            llimpl.compile_add_jump_target(c, compiled_version)
        elif op.opnum == rop.FINISH:
            faildescr = op.descr
            index = self.get_fail_descr_number(faildescr)
            llimpl.compile_add_fail(c, index)
        else:
            assert False, "unknown operation"

    def _execute_token(self, loop_token):
        compiled_version = loop_token._llgraph_compiled_version
        frame = llimpl.new_frame(self.memo_cast, self.is_oo, self)
        # setup the frame
        llimpl.frame_clear(frame, compiled_version)
        # run the loop
        fail_index = llimpl.frame_execute(frame)
        # we hit a FAIL operation.
        self.latest_frame = frame
        return fail_index

    def execute_token(self, loop_token):
        """Calls the assembler generated for the given loop.
        Returns the ResOperation that failed, of type rop.FAIL.
        """
        fail_index = self._execute_token(loop_token)
        return self.get_fail_descr_from_number(fail_index)

    def set_future_value_int(self, index, intvalue):
        llimpl.set_future_value_int(index, intvalue)

    def set_future_value_ref(self, index, objvalue):
        llimpl.set_future_value_ref(index, objvalue)

    def set_future_value_float(self, index, floatvalue):
        llimpl.set_future_value_float(index, floatvalue)

    def get_latest_value_int(self, index):
        return llimpl.frame_int_getvalue(self.latest_frame, index)

    def get_latest_value_ref(self, index):
        return llimpl.frame_ptr_getvalue(self.latest_frame, index)

    def get_latest_value_float(self, index):
        return llimpl.frame_float_getvalue(self.latest_frame, index)

    def get_latest_force_token(self):
        token = llimpl.get_frame_forced_token(self.latest_frame)
        return self.cast_adr_to_int(token)

    def make_boxes_from_latest_values(self, faildescr):
        inputargs_and_holes = []
        for i in range(len(faildescr._fail_args_types)):
            boxtype = faildescr._fail_args_types[i]
            if boxtype == history.INT:
                box = history.BoxInt(self.get_latest_value_int(i))
            elif boxtype == history.REF:
                box = self.ts.BoxRef(self.get_latest_value_ref(i))
            elif boxtype == history.FLOAT:
                box = history.BoxFloat(self.get_latest_value_float(i))
            elif boxtype == history.HOLE:
                box = None
            else:
                assert False, "bad box type: num=%d" % ord(boxtype)
            inputargs_and_holes.append(box)
        return inputargs_and_holes

    # ----------

    def get_exception(self):
        return self.cast_adr_to_int(llimpl.get_exception())

    def get_exc_value(self):
        return llimpl.get_exc_value()

    def clear_exception(self):
        llimpl.clear_exception()

    def get_overflow_error(self):
        return (self.cast_adr_to_int(llimpl.get_overflow_error()),
                llimpl.get_overflow_error_value())

    def get_zero_division_error(self):
        return (self.cast_adr_to_int(llimpl.get_zero_division_error()),
                llimpl.get_zero_division_error_value())

    def sizeof(self, S):
        assert not isinstance(S, lltype.Ptr)
        return self.getdescr(symbolic.get_size(S))

    def cast_adr_to_int(self, adr):
        return llimpl.cast_adr_to_int(self.memo_cast, adr)

    def cast_int_to_adr(self, int):
        return llimpl.cast_int_to_adr(self.memo_cast, int)

    def cast_gcref_to_int(self, gcref):
        return self.cast_adr_to_int(llmemory.cast_ptr_to_adr(gcref))



class LLtypeCPU(BaseCPU):
    is_oo = False
    ts = llhelper

    def __init__(self, *args, **kwds):
        BaseCPU.__init__(self, *args, **kwds)
        self.fielddescrof_vtable = self.fielddescrof(rclass.OBJECT, 'typeptr')
        
    def fielddescrof(self, S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname)
        token = history.getkind(getattr(S, fieldname))
        return self.getdescr(ofs, token[0], name=fieldname)

    def calldescrof(self, FUNC, ARGS, RESULT, extrainfo=None):
        token = history.getkind(RESULT)
        return self.getdescr(0, token[0], extrainfo=extrainfo)

    def get_exception(self):
        return self.cast_adr_to_int(llimpl.get_exception())

    def get_exc_value(self):
        return llimpl.get_exc_value()

    def arraydescrof(self, A):
        assert isinstance(A, lltype.GcArray)
        assert A.OF != lltype.Void
        size = symbolic.get_size(A)
        token = history.getkind(A.OF)
        return self.getdescr(size, token[0])

    # ---------- the backend-dependent operations ----------

    def do_arraylen_gc(self, arraybox, arraydescr):
        array = arraybox.getref_base()
        return history.BoxInt(llimpl.do_arraylen_gc(arraydescr, array))

    def do_strlen(self, stringbox):
        string = stringbox.getref_base()
        return history.BoxInt(llimpl.do_strlen(0, string))

    def do_strgetitem(self, stringbox, indexbox):
        string = stringbox.getref_base()
        index = indexbox.getint()
        return history.BoxInt(llimpl.do_strgetitem(0, string, index))

    def do_unicodelen(self, stringbox):
        string = stringbox.getref_base()
        return history.BoxInt(llimpl.do_unicodelen(0, string))

    def do_unicodegetitem(self, stringbox, indexbox):
        string = stringbox.getref_base()
        index = indexbox.getint()
        return history.BoxInt(llimpl.do_unicodegetitem(0, string, index))

    def do_getarrayitem_gc(self, arraybox, indexbox, arraydescr):
        assert isinstance(arraydescr, Descr)
        array = arraybox.getref_base()
        index = indexbox.getint()
        if arraydescr.typeinfo == REF:
            return history.BoxPtr(llimpl.do_getarrayitem_gc_ptr(array, index))
        elif arraydescr.typeinfo == INT:
            return history.BoxInt(llimpl.do_getarrayitem_gc_int(array, index,
                                                               self.memo_cast))
        elif arraydescr.typeinfo == FLOAT:
            return history.BoxFloat(llimpl.do_getarrayitem_gc_float(array,
                                                                    index))
        else:
            raise NotImplementedError

    def do_getfield_gc(self, structbox, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = structbox.getref_base()
        if fielddescr.typeinfo == REF:
            return history.BoxPtr(llimpl.do_getfield_gc_ptr(struct,
                                                            fielddescr.ofs))
        elif fielddescr.typeinfo == INT:
            return history.BoxInt(llimpl.do_getfield_gc_int(struct,
                                                            fielddescr.ofs,
                                                            self.memo_cast))
        elif fielddescr.typeinfo == FLOAT:
            return history.BoxFloat(llimpl.do_getfield_gc_float(struct,
                                                            fielddescr.ofs))
        else:
            raise NotImplementedError

    def do_getfield_raw(self, structbox, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = self.cast_int_to_adr(structbox.getint())
        if fielddescr.typeinfo == REF:
            return history.BoxPtr(llimpl.do_getfield_raw_ptr(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))
        elif fielddescr.typeinfo == INT:
            return history.BoxInt(llimpl.do_getfield_raw_int(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))
        elif fielddescr.typeinfo == FLOAT:
            return history.BoxFloat(llimpl.do_getfield_raw_float(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))
        else:
            raise NotImplementedError

    def do_new(self, size):
        assert isinstance(size, Descr)
        return history.BoxPtr(llimpl.do_new(size.ofs))

    def do_new_with_vtable(self, vtablebox):
        vtable = vtablebox.getint()
        size = self.class_sizes[vtable]
        result = llimpl.do_new(size.ofs)
        llimpl.do_setfield_gc_int(result, self.fielddescrof_vtable.ofs,
                                  vtable, self.memo_cast)
        return history.BoxPtr(result)

    def do_new_array(self, countbox, size):
        assert isinstance(size, Descr)
        count = countbox.getint()
        return history.BoxPtr(llimpl.do_new_array(size.ofs, count))

    def do_setarrayitem_gc(self, arraybox, indexbox, newvaluebox, arraydescr):
        assert isinstance(arraydescr, Descr)
        array = arraybox.getref_base()
        index = indexbox.getint()
        if arraydescr.typeinfo == REF:
            newvalue = newvaluebox.getref_base()
            llimpl.do_setarrayitem_gc_ptr(array, index, newvalue)
        elif arraydescr.typeinfo == INT:
            newvalue = newvaluebox.getint()
            llimpl.do_setarrayitem_gc_int(array, index, newvalue,
                                          self.memo_cast)
        elif arraydescr.typeinfo == FLOAT:
            newvalue = newvaluebox.getfloat()
            llimpl.do_setarrayitem_gc_float(array, index, newvalue)
        else:
            raise NotImplementedError

    def do_setfield_gc(self, structbox, newvaluebox, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = structbox.getref_base()
        if fielddescr.typeinfo == REF:
            newvalue = newvaluebox.getref_base()
            llimpl.do_setfield_gc_ptr(struct, fielddescr.ofs, newvalue)
        elif fielddescr.typeinfo == INT:
            newvalue = newvaluebox.getint()
            llimpl.do_setfield_gc_int(struct, fielddescr.ofs, newvalue,
                                      self.memo_cast)
        elif fielddescr.typeinfo == FLOAT:
            newvalue = newvaluebox.getfloat()
            llimpl.do_setfield_gc_float(struct, fielddescr.ofs, newvalue)
        else:
            raise NotImplementedError

    def do_setfield_raw(self, structbox, newvaluebox, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = self.cast_int_to_adr(structbox.getint())
        if fielddescr.typeinfo == REF:
            newvalue = newvaluebox.getref_base()
            llimpl.do_setfield_raw_ptr(struct, fielddescr.ofs, newvalue,
                                       self.memo_cast)
        elif fielddescr.typeinfo == INT:
            newvalue = newvaluebox.getint()
            llimpl.do_setfield_raw_int(struct, fielddescr.ofs, newvalue,
                                       self.memo_cast)
        elif fielddescr.typeinfo == FLOAT:
            newvalue = newvaluebox.getfloat()
            llimpl.do_setfield_raw_float(struct, fielddescr.ofs, newvalue,
                                         self.memo_cast)
        else:
            raise NotImplementedError

    def do_same_as(self, box1):
        return box1.clonebox()

    def do_newstr(self, lengthbox):
        length = lengthbox.getint()
        return history.BoxPtr(llimpl.do_newstr(0, length))

    def do_newunicode(self, lengthbox):
        length = lengthbox.getint()
        return history.BoxPtr(llimpl.do_newunicode(0, length))

    def do_strsetitem(self, stringbox, indexbox, newvaluebox):
        string = stringbox.getref_base()
        index = indexbox.getint()
        newvalue = newvaluebox.getint()
        llimpl.do_strsetitem(0, string, index, newvalue)

    def do_unicodesetitem(self, stringbox, indexbox, newvaluebox):
        string = stringbox.getref_base()
        index = indexbox.getint()
        newvalue = newvaluebox.getint()
        llimpl.do_unicodesetitem(0, string, index, newvalue)

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, Descr)
        func = args[0].getint()
        for arg in args[1:]:
            if arg.type == REF:
                llimpl.do_call_pushptr(arg.getref_base())
            elif arg.type == FLOAT:
                llimpl.do_call_pushfloat(arg.getfloat())
            else:
                llimpl.do_call_pushint(arg.getint())
        if calldescr.typeinfo == REF:
            return history.BoxPtr(llimpl.do_call_ptr(func, self.memo_cast))
        elif calldescr.typeinfo == INT:
            return history.BoxInt(llimpl.do_call_int(func, self.memo_cast))
        elif calldescr.typeinfo == FLOAT:
            return history.BoxFloat(llimpl.do_call_float(func, self.memo_cast))
        elif calldescr.typeinfo == 'v':  # void
            llimpl.do_call_void(func, self.memo_cast)
        else:
            raise NotImplementedError

    def do_cast_ptr_to_int(self, ptrbox):
        return history.BoxInt(llimpl.cast_to_int(ptrbox.getref_base(),
                                                        self.memo_cast))

    def force(self, force_token):
        token = self.cast_int_to_adr(force_token)
        frame = llimpl.get_forced_token_frame(token)
        fail_index = llimpl.force(frame)
        self.latest_frame = frame
        return self.get_fail_descr_from_number(fail_index)


class OOtypeCPU(BaseCPU):
    is_oo = True
    ts = oohelper

    @staticmethod
    def fielddescrof(T, fieldname):
        # use class where the field is really defined as a key
        T1, _ = T._lookup_field(fieldname)
        return FieldDescr.new(T1, fieldname)

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT, extrainfo=None):
        return StaticMethDescr.new(FUNC, ARGS, RESULT, extrainfo)

    @staticmethod
    def methdescrof(SELFTYPE, methname):
        return MethDescr.new(SELFTYPE, methname)

    @staticmethod
    def typedescrof(TYPE):
        return TypeDescr.new(TYPE)

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, ootype.Array)
        TYPE = A.ITEM
        return TypeDescr.new(TYPE)

    def typedescr2classbox(self, descr):
        assert isinstance(descr, TypeDescr)
        return history.ConstObj(ootype.cast_to_object(
                            ootype.runtimeClass(descr.TYPE)))

    def get_exception(self):
        if llimpl._last_exception:
            e = llimpl._last_exception.args[0]
            return ootype.cast_to_object(e)
        else:
            return ootype.NULL
        
    def get_exc_value(self):
        if llimpl._last_exception:
            earg = llimpl._last_exception.args[1]
            return ootype.cast_to_object(earg)
        else:
            return ootype.NULL

    def get_overflow_error(self):
        ll_err = llimpl._get_error(OverflowError)
        return (ootype.cast_to_object(ll_err.args[0]),
                ootype.cast_to_object(ll_err.args[1]))

    def get_zero_division_error(self):
        ll_err = llimpl._get_error(ZeroDivisionError)
        return (ootype.cast_to_object(ll_err.args[0]),
                ootype.cast_to_object(ll_err.args[1]))

    def do_new_with_vtable(self, clsbox):
        cls = clsbox.getref_base()
        typedescr = self.class_sizes[cls]
        return typedescr.create()

    def do_new_array(self, lengthbox, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.create_array(lengthbox)

    def do_new(self, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.create()

    def do_runtimenew(self, classbox):
        "NOT_RPYTHON"
        classobj = classbox.getref(ootype.Class)
        res = ootype.runtimenew(classobj)
        return history.BoxObj(ootype.cast_to_object(res))

    def do_instanceof(self, box1, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.instanceof(box1)

    def do_getfield_gc(self, box1, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.getfield(box1)

    def do_setfield_gc(self, box1, box2, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.setfield(box1, box2)

    def do_getarrayitem_gc(self, box1, box2, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.getarrayitem(box1, box2)

    def do_setarrayitem_gc(self, box1, box2, box3, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.setarrayitem(box1, box2, box3)

    def do_arraylen_gc(self, box1, typedescr):
        assert isinstance(typedescr, TypeDescr)
        return typedescr.getarraylength(box1)

    def do_call(self, args, descr):
        assert isinstance(descr, StaticMethDescr)
        funcbox = args[0]
        argboxes = args[1:]
        x = descr.callfunc(funcbox, argboxes)
        # XXX: return None if RESULT is Void
        return x

    def do_oosend(self, args, descr):
        assert isinstance(descr, MethDescr)
        selfbox = args[0]
        argboxes = args[1:]
        x = descr.callmeth(selfbox, argboxes)
        # XXX: return None if METH.RESULT is Void
        return x
    

def make_getargs(ARGS):
    argsiter = unrolling_iterable(ARGS)
    args_n = len([ARG for ARG in ARGS if ARG is not ootype.Void])
    def getargs(argboxes):
        funcargs = ()
        assert len(argboxes) == args_n
        i = 0
        for ARG in argsiter:
            if ARG is ootype.Void:
                funcargs += (None,)
            else:
                box = argboxes[i]
                i+=1
                funcargs += (unwrap(ARG, box),)
        return funcargs
    return getargs

def boxresult(RESULT, result):
    if isinstance(RESULT, ootype.OOType):
        return history.BoxObj(ootype.cast_to_object(result))
    elif RESULT is lltype.Float:
        return history.BoxFloat(result)
    else:
        return history.BoxInt(lltype.cast_primitive(ootype.Signed, result))
boxresult._annspecialcase_ = 'specialize:arg(0)'


class KeyManager(object):
    """
    Helper class to convert arbitrary dictionary keys to integers.
    """    

    def __init__(self):
        self.keys = {}

    def getkey(self, key):
        try:
            return self.keys[key]
        except KeyError:
            n = len(self.keys)
            self.keys[key] = n
            return n

    def _freeze_(self):
        raise Exception("KeyManager is not supposed to be turned into a pbc")


descr_cache = {}
class OODescr(history.AbstractDescr):

    @classmethod
    def new(cls, *args):
        'NOT_RPYTHON'
        key = (cls, args)
        try:
            return descr_cache[key]
        except KeyError:
            res = cls(*args)
            descr_cache[key] = res
            return res

class StaticMethDescr(OODescr):

    def __init__(self, FUNC, ARGS, RESULT, extrainfo=None):
        self.FUNC = FUNC
        getargs = make_getargs(FUNC.ARGS)
        def callfunc(funcbox, argboxes):
            funcobj = funcbox.getref(FUNC)
            funcargs = getargs(argboxes)
            res = llimpl.call_maybe_on_top_of_llinterp(funcobj, funcargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callfunc = callfunc
        self.extrainfo = extrainfo

    def get_extra_info(self):
        return self.extrainfo

class MethDescr(history.AbstractMethDescr):

    callmeth = None

    new = classmethod(OODescr.new.im_func)

    def __init__(self, SELFTYPE, methname):
        _, meth = SELFTYPE._lookup(methname)
        METH = ootype.typeOf(meth)
        self.SELFTYPE = SELFTYPE
        self.METH = METH
        self.methname = methname
        RESULT = METH.RESULT
        getargs = make_getargs(METH.ARGS)
        def callmeth(selfbox, argboxes):
            selfobj = selfbox.getref(SELFTYPE)
            meth = getattr(selfobj, methname)
            methargs = getargs(argboxes)
            res = llimpl.call_maybe_on_top_of_llinterp(meth, methargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callmeth = callmeth

    def __repr__(self):
        return '<MethDescr %r>' % self.methname

class TypeDescr(OODescr):

    create = None

    def __init__(self, TYPE):
        self.TYPE = TYPE
        self.ARRAY = ARRAY = ootype.Array(TYPE)
        def create():
            return boxresult(TYPE, ootype.new(TYPE))
        
        def create_array(lengthbox):
            n = lengthbox.getint()
            return boxresult(ARRAY, ootype.oonewarray(ARRAY, n))

        def getarrayitem(arraybox, ibox):
            array = arraybox.getref(ARRAY)
            i = ibox.getint()
            return boxresult(TYPE, array.ll_getitem_fast(i))

        def setarrayitem(arraybox, ibox, valuebox):
            array = arraybox.getref(ARRAY)
            i = ibox.getint()
            value = unwrap(TYPE, valuebox)
            array.ll_setitem_fast(i, value)

        def getarraylength(arraybox):
            array = arraybox.getref(ARRAY)
            return boxresult(ootype.Signed, array.ll_length())

        def instanceof(box):
            obj = box.getref(ootype.ROOT)
            return history.BoxInt(ootype.instanceof(obj, TYPE))

        self.create = create
        self.create_array = create_array
        self.getarrayitem = getarrayitem
        self.setarrayitem = setarrayitem
        self.getarraylength = getarraylength
        self.instanceof = instanceof
        self._is_array_of_pointers = (history.getkind(TYPE) == 'ref')
        self._is_array_of_floats = (history.getkind(TYPE) == 'float')

    def is_array_of_pointers(self):
        # for arrays, TYPE is the type of the array item.
        return self._is_array_of_pointers

    def is_array_of_floats(self):
        # for arrays, TYPE is the type of the array item.
        return self._is_array_of_floats

    def __repr__(self):
        return '<TypeDescr %s>' % self.TYPE._short_name()

class FieldDescr(OODescr):

    getfield = None
    _keys = KeyManager()

    def __init__(self, TYPE, fieldname):
        self.TYPE = TYPE
        self.fieldname = fieldname

        _, T = TYPE._lookup_field(fieldname)
        def getfield(objbox):
            obj = objbox.getref(TYPE)
            value = getattr(obj, fieldname)
            return boxresult(T, value)
        def setfield(objbox, valuebox):
            obj = objbox.getref(TYPE)
            value = unwrap(T, valuebox)
            setattr(obj, fieldname, value)
            
        self.getfield = getfield
        self.setfield = setfield
        self._is_pointer_field = (history.getkind(T) == 'ref')
        self._is_float_field = (history.getkind(T) == 'float')

    def sort_key(self):
        return self._keys.getkey((self.TYPE, self.fieldname))

    def is_pointer_field(self):
        return self._is_pointer_field

    def is_float_field(self):
        return self._is_float_field

    def equals(self, other):
        return self.TYPE == other.TYPE and \
            self.fieldname == other.fieldname

    def __repr__(self):
        return '<FieldDescr %r>' % self.fieldname


# ____________________________________________________________

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(LLtypeCPU)
pypy.jit.metainterp.executor.make_execute_list(OOtypeCPU)
