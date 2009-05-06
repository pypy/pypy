"""
Minimal-API wrapper around the llinterpreter to run operations.
"""

import sys
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.llinterp import LLInterpreter
from pypy.jit.metainterp import history
from pypy.jit.metainterp.warmspot import unwrap
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.backend import model
from pypy.jit.backend.llgraph import llimpl, symbolic


class MiniStats:
    pass


class Descr(history.AbstractDescr):
    name = None
    ofs = -1
    type = '?'
    
    def __init__(self, ofs, type='?'):
        self.ofs = ofs
        self.type = type

    def __hash__(self):
        return hash((self.ofs, self.type))

    def __eq__(self, other):
        if not isinstance(other, Descr):
            return NotImplemented
        return self.ofs == other.ofs and self.type == other.type

    def __ne__(self, other):
        if not isinstance(other, Descr):
            return NotImplemented
        return self.ofs != other.ofs or self.type != other.type

    def sort_key(self):
        return self.ofs

    def equals(self, other):
        if not isinstance(other, Descr):
            return False
        return self.sort_key() == other.sort_key()

    def __lt__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __le__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __gt__(self, other):
        raise TypeError("cannot use comparison on Descrs")
    def __ge__(self, other):
        raise TypeError("cannot use comparison on Descrs")

    def __repr__(self):
        if self.name is not None:
            return '<Descr %r, %r, %r>' % (self.ofs, self.type, self.name)
        return '<Descr %r, %r>' % (self.ofs, self.type)


history.TreeLoop._compiled_version = lltype.nullptr(llimpl.COMPILEDLOOP.TO)


class BaseCPU(model.AbstractCPU):

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None):
        self.rtyper = rtyper
        self.translate_support_code = translate_support_code
        self.stats = stats or MiniStats()
        self.stats.exec_counters = {}
        self.stats.exec_jumps = 0
        self.stats.exec_conditional_jumps = 0
        self.memo_cast = llimpl.new_memo_cast()
        self.fail_ops = []
        llimpl._stats = self.stats
        llimpl._llinterp = LLInterpreter(self.rtyper)
        if translate_support_code:
            self.mixlevelann = annmixlevel
        self._future_values = []

    def _freeze_(self):
        assert self.translate_support_code
        return False

    def compile_operations(self, loop):
        """In a real assembler backend, this should assemble the given
        list of operations.  Here we just generate a similar CompiledLoop
        instance.  The code here is RPython, whereas the code in llimpl
        is not.
        """
        c = llimpl.compile_start()
        prev_c = loop._compiled_version
        loop._compiled_version = c
        var2index = {}
        for box in loop.inputargs:
            if isinstance(box, history.BoxInt):
                var2index[box] = llimpl.compile_start_int_var(c)
            elif isinstance(box, history.BoxPtr):
                var2index[box] = llimpl.compile_start_ptr_var(c)
            elif self.is_oo and isinstance(box, history.BoxObj):
                var2index[box] = llimpl.compile_start_obj_var(c)
            else:
                raise Exception("box is: %r" % (box,))
        self._compile_branch(c, loop.operations, var2index)
        # We must redirect code jumping to the old loop so that it goes
        # to the new loop.
        if prev_c:
            llimpl.compile_redirect_code(prev_c, c)

    def _compile_branch(self, c, operations, var2index):
        for op in operations:
            llimpl.compile_add(c, op.opnum)
            if isinstance(op.descr, Descr):
                llimpl.compile_add_descr(c, op.descr.ofs, op.descr.type)
            if self.is_oo and isinstance(op.descr, (OODescr, MethDescr)):
                # hack hack, not rpython
                c._obj.externalobj.operations[-1].descr = op.descr
            for x in op.args:
                if isinstance(x, history.Box):
                    llimpl.compile_add_var(c, var2index[x])
                elif isinstance(x, history.ConstInt):
                    llimpl.compile_add_int_const(c, x.value)
                elif isinstance(x, history.ConstPtr):
                    llimpl.compile_add_ptr_const(c, x.value)
                elif isinstance(x, history.ConstAddr):
                    llimpl.compile_add_int_const(c, x.getint())
                elif self.is_oo and isinstance(x, history.ConstObj):
                    llimpl.compile_add_ptr_const(c, x.value, ootype.Object)
                else:
                    raise Exception("%s args contain: %r" % (op.getopname(),
                                                             x))
            if op.is_guard():
                c2 = llimpl.compile_suboperations(c)
                self._compile_branch(c2, op.suboperations, var2index.copy())
            x = op.result
            if x is not None:
                if isinstance(x, history.BoxInt):
                    var2index[x] = llimpl.compile_add_int_result(c)
                elif isinstance(x, history.BoxPtr):
                    var2index[x] = llimpl.compile_add_ptr_result(c)
                elif self.is_oo and isinstance(x, history.BoxObj):
                    var2index[x] = llimpl.compile_add_ptr_result(c, ootype.Object)
                else:
                    raise Exception("%s.result contain: %r" % (op.getopname(),
                                                               x))
        op = operations[-1]
        assert op.is_final()
        if op.opnum == rop.JUMP:
            llimpl.compile_add_jump_target(c, op.jump_target._compiled_version)
        elif op.opnum == rop.FAIL:
            llimpl.compile_add_fail(c, len(self.fail_ops))
            self.fail_ops.append(op)

    def execute_operations(self, loop):
        """Calls the assembler generated for the given loop.
        Returns the ResOperation that failed, of type rop.FAIL.
        """
        frame = llimpl.new_frame(self.memo_cast, self.is_oo)
        # setup the frame
        llimpl.frame_clear(frame, loop._compiled_version)
        # run the loop
        fail_index = llimpl.frame_execute(frame)
        # we hit a FAIL operation.
        self.latest_frame = frame
        return self.fail_ops[fail_index]

    def set_future_value_int(self, index, intvalue):
        llimpl.set_future_value_int(index, intvalue)

    def set_future_value_ptr(self, index, ptrvalue):
        llimpl.set_future_value_ptr(index, ptrvalue)

    def set_future_value_obj(self, index, objvalue):
        llimpl.set_future_value_obj(index, objvalue)

    def get_latest_value_int(self, index):
        return llimpl.frame_int_getvalue(self.latest_frame, index)

    def get_latest_value_ptr(self, index):
        return llimpl.frame_ptr_getvalue(self.latest_frame, index)

    def get_latest_value_obj(self, index):
        return llimpl.frame_ptr_getvalue(self.latest_frame, index)

    # ----------

    def get_exception(self):
        return self.cast_adr_to_int(llimpl.get_exception())

    def get_exc_value(self):
        return llimpl.get_exc_value()

    def clear_exception(self):
        llimpl.clear_exception()

    def set_overflow_error(self):
        llimpl.set_overflow_error()

    def set_zero_division_error(self):
        llimpl.set_zero_division_error()

    @staticmethod
    def sizeof(S):
        return Descr(symbolic.get_size(S))

    @staticmethod
    def numof(S):
        return 4

    ##addresssuffix = '4'

    def cast_adr_to_int(self, adr):
        return llimpl.cast_adr_to_int(self.memo_cast, adr)

    def cast_int_to_adr(self, int):
        return llimpl.cast_int_to_adr(self.memo_cast, int)



class LLtypeCPU(BaseCPU):
    is_oo = False

    def __init__(self, *args, **kwds):
        BaseCPU.__init__(self, *args, **kwds)
        self.fielddescrof_vtable = self.fielddescrof(rclass.OBJECT, 'typeptr')
        
    @staticmethod
    def fielddescrof(S, fieldname):
        ofs, size = symbolic.get_field_token(S, fieldname)
        token = history.getkind(getattr(S, fieldname))
        res = Descr(ofs, token[0])
        res.name = fieldname
        return res

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT):
        token = history.getkind(RESULT)
        return Descr(0, token[0])

    def get_exception(self):
        return self.cast_adr_to_int(llimpl.get_exception())

    def get_exc_value(self):
        return llimpl.get_exc_value()

    @staticmethod
    def arraydescrof(A):
        assert isinstance(A, lltype.GcArray)
        size = symbolic.get_size(A)
        token = history.getkind(A.OF)
        return Descr(size, token[0])

    # ---------- the backend-dependent operations ----------

    def do_arraylen_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        return history.BoxInt(llimpl.do_arraylen_gc(arraydescr, array))

    def do_strlen(self, args, descr=None):
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_strlen(0, string))

    def do_strgetitem(self, args, descr=None):
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_strgetitem(0, string, index))

    def do_unicodelen(self, args, descr=None):
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_unicodelen(0, string))

    def do_unicodegetitem(self, args, descr=None):
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_unicodegetitem(0, string, index))

    def do_getarrayitem_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        index = args[1].getint()
        if arraydescr.type == 'p':
            return history.BoxPtr(llimpl.do_getarrayitem_gc_ptr(array, index))
        else:
            return history.BoxInt(llimpl.do_getarrayitem_gc_int(array, index,
                                                               self.memo_cast))

    def do_getfield_gc(self, args, fielddescr):
        struct = args[0].getptr_base()
        if fielddescr.type == 'p':
            return history.BoxPtr(llimpl.do_getfield_gc_ptr(struct,
                                                            fielddescr.ofs))
        else:
            return history.BoxInt(llimpl.do_getfield_gc_int(struct,
                                                            fielddescr.ofs,
                                                            self.memo_cast))
    def do_getfield_raw(self, args, fielddescr):
        struct = self.cast_int_to_adr(args[0].getint())
        if fielddescr.type == 'p':
            return history.BoxPtr(llimpl.do_getfield_raw_ptr(struct,
                                                             fielddescr.ofs))
        else:
            return history.BoxInt(llimpl.do_getfield_raw_int(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))

    def do_new(self, args, size):
        return history.BoxPtr(llimpl.do_new(size.ofs))

    def do_new_with_vtable(self, args, size):
        vtable = args[0].getint()
        result = llimpl.do_new(size.ofs)
        llimpl.do_setfield_gc_int(result, self.fielddescrof_vtable.ofs,
                                  vtable, self.memo_cast)
        return history.BoxPtr(result)

    def do_new_array(self, args, size):
        count = args[0].getint()
        return history.BoxPtr(llimpl.do_new_array(size.ofs, count))

    def do_setarrayitem_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        index = args[1].getint()
        if arraydescr.type == 'p':
            newvalue = args[2].getptr_base()
            llimpl.do_setarrayitem_gc_ptr(array, index, newvalue)
        else:
            newvalue = args[2].getint()
            llimpl.do_setarrayitem_gc_int(array, index, newvalue,
                                          self.memo_cast)

    def do_setfield_gc(self, args, fielddescr):
        struct = args[0].getptr_base()
        if fielddescr.type == 'p':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_gc_ptr(struct, fielddescr.ofs, newvalue)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_gc_int(struct, fielddescr.ofs, newvalue,
                                      self.memo_cast)

    def do_setfield_raw(self, args, fielddescr):
        struct = self.cast_int_to_adr(args[0].getint())
        if fielddescr.type == 'p':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_raw_ptr(struct, fielddescr.ofs, newvalue)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_raw_int(struct, fielddescr.ofs, newvalue,
                                       self.memo_cast)

    def do_newstr(self, args, descr=None):
        length = args[0].getint()
        return history.BoxPtr(llimpl.do_newstr(0, length))

    def do_newunicode(self, args, descr=None):
        length = args[0].getint()
        return history.BoxPtr(llimpl.do_newunicode(0, length))

    def do_strsetitem(self, args, descr=None):
        string = args[0].getptr_base()
        index = args[1].getint()
        newvalue = args[2].getint()
        llimpl.do_strsetitem(0, string, index, newvalue)

    def do_unicodesetitem(self, args, descr=None):
        string = args[0].getptr_base()
        index = args[1].getint()
        newvalue = args[2].getint()
        llimpl.do_unicodesetitem(0, string, index, newvalue)

    def do_call(self, args, calldescr):
        func = args[0].getint()
        for arg in args[1:]:
            if (isinstance(arg, history.BoxPtr) or
                isinstance(arg, history.ConstPtr)):
                llimpl.do_call_pushptr(arg.getptr_base())
            else:
                llimpl.do_call_pushint(arg.getint())
        if calldescr.type == 'p':
            return history.BoxPtr(llimpl.do_call_ptr(func, self.memo_cast))
        elif calldescr.type == 'i':
            return history.BoxInt(llimpl.do_call_int(func, self.memo_cast))
        else:  # calldescr.type == 'v'  # void
            llimpl.do_call_void(func, self.memo_cast)

    def do_cast_int_to_ptr(self, args, descr=None):
        return history.BoxPtr(llimpl.cast_from_int(llmemory.GCREF,
                                                   args[0].getint(),
                                                   self.memo_cast))

    def do_cast_ptr_to_int(self, args, descr=None):
        return history.BoxInt(llimpl.cast_to_int(args[0].getptr_base(),
                                                        self.memo_cast))

class OOtypeCPU(BaseCPU):
    is_oo = True

    @staticmethod
    def fielddescrof(T, fieldname):
        return FieldDescr.new(T, fieldname)

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT):
        return StaticMethDescr.new(FUNC, ARGS, RESULT)

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

    def do_new_with_vtable(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1 # but we don't need it, so ignore
        return typedescr.create()

    def do_new_array(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.create_array(args[0])

    def do_runtimenew(self, args, descr):
        "NOT_RPYTHON"
        classbox = args[0]
        classobj = ootype.cast_from_object(ootype.Class, classbox.getobj())
        res = ootype.runtimenew(classobj)
        return history.BoxObj(ootype.cast_to_object(res))

    def do_instanceof(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.instanceof(args[0])

    def do_getfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.getfield(args[0])

    def do_setfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        return fielddescr.setfield(args[0], args[1])

    def do_getarrayitem_gc(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 2
        return typedescr.getarrayitem(*args)

    def do_setarrayitem_gc(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 3
        return typedescr.setarrayitem(*args)

    def do_arraylen_gc(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.getarraylength(*args)

    def do_call(self, args, descr):
        assert isinstance(descr, StaticMethDescr)
        funcbox = args[0]
        argboxes = args[1:]
        x = descr.callfunc(funcbox, argboxes)
        # XXX: return None if RESULT is Void
        return x

    def do_oosend(self, args, descr=None):
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

    def __init__(self, FUNC, ARGS, RESULT):
        self.FUNC = FUNC
        getargs = make_getargs(FUNC.ARGS)
        def callfunc(funcbox, argboxes):
            funcobj = ootype.cast_from_object(FUNC, funcbox.getobj())
            funcargs = getargs(argboxes)
            res = llimpl.call_maybe_on_top_of_llinterp(funcobj, funcargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callfunc = callfunc

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
            selfobj = ootype.cast_from_object(SELFTYPE, selfbox.getobj())
            meth = getattr(selfobj, methname)
            methargs = getargs(argboxes)
            res = llimpl.call_maybe_on_top_of_llinterp(meth, methargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callmeth = callmeth

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
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            i = ibox.getint()
            return boxresult(TYPE, array.ll_getitem_fast(i))

        def setarrayitem(arraybox, ibox, valuebox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            i = ibox.getint()
            value = unwrap(TYPE, valuebox)
            array.ll_setitem_fast(i, value)

        def getarraylength(arraybox):
            array = ootype.cast_from_object(ARRAY, arraybox.getobj())
            return boxresult(ootype.Signed, array.ll_length())

        def instanceof(box):
            obj = ootype.cast_from_object(ootype.ROOT, box.getobj())
            return history.BoxInt(ootype.instanceof(obj, TYPE))

        self.create = create
        self.create_array = create_array
        self.getarrayitem = getarrayitem
        self.setarrayitem = setarrayitem
        self.getarraylength = getarraylength
        self.instanceof = instanceof

class FieldDescr(OODescr):

    getfield = None
    _keys = KeyManager()

    def __init__(self, TYPE, fieldname):
        self.TYPE = TYPE
        self.fieldname = fieldname

        _, T = TYPE._lookup_field(fieldname)
        def getfield(objbox):
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = getattr(obj, fieldname)
            return boxresult(T, value)
        def setfield(objbox, valuebox):
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = unwrap(T, valuebox)
            setattr(obj, fieldname, value)
            
        self.getfield = getfield
        self.setfield = setfield

    def sort_key(self):
        return self._keys.getkey((self.TYPE, self.fieldname))

    def equals(self, other):
        return self.TYPE == other.TYPE and \
            self.fieldname == other.fieldname


# ____________________________________________________________

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(LLtypeCPU)
pypy.jit.metainterp.executor.make_execute_list(OOtypeCPU)
