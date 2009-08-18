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
    typeinfo = '?'
    
    def __init__(self, ofs, typeinfo='?'):
        self.ofs = ofs
        self.typeinfo = typeinfo

    def __hash__(self):
        return hash((self.ofs, self.typeinfo))

    def __eq__(self, other):
        if not isinstance(other, Descr):
            return NotImplemented
        return self.ofs == other.ofs and self.typeinfo == other.typeinfo

    def __ne__(self, other):
        if not isinstance(other, Descr):
            return NotImplemented
        return self.ofs != other.ofs or self.typeinfo != other.typeinfo

    def sort_key(self):
        return self.ofs

    def is_pointer_field(self):
        return self.typeinfo == 'p'

    def is_array_of_pointers(self):
        return self.typeinfo == 'p'

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
            return '<Descr %r, %r, %r>' % (self.ofs, self.typeinfo, self.name)
        return '<Descr %r, %r>' % (self.ofs, self.typeinfo)


history.TreeLoop._compiled_version = lltype.nullptr(llimpl.COMPILEDLOOP.TO)


class BaseCPU(model.AbstractCPU):

    def __init__(self, rtyper, stats=None, translate_support_code=False,
                 annmixlevel=None, gcdescr=None):
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

    def set_class_sizes(self, class_sizes):
        self.class_sizes = class_sizes
        for vtable, size in class_sizes.items():
            if not self.is_oo:
                size = size.ofs
            llimpl.set_class_size(self.memo_cast, vtable, size)

    def compile_operations(self, loop, bridge=None):
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
            descr = op.descr
            if isinstance(descr, Descr):
                llimpl.compile_add_descr(c, descr.ofs, descr.typeinfo)
            if self.is_oo and isinstance(descr, (OODescr, MethDescr)):
                # hack hack, not rpython
                c._obj.externalobj.operations[-1].descr = descr
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

    def get_overflow_error(self):
        return (self.cast_adr_to_int(llimpl.get_overflow_error()),
                llimpl.get_overflow_error_value())

    def get_zero_division_error(self):
        return (self.cast_adr_to_int(llimpl.get_zero_division_error()),
                llimpl.get_zero_division_error_value())

    def get_overflow_flag(self):
        return llimpl.get_overflow_flag()

    def set_overflow_flag(self, flag):
        llimpl.set_overflow_flag(flag)

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
        assert A.OF != lltype.Void
        size = symbolic.get_size(A)
        token = history.getkind(A.OF)
        return Descr(size, token[0])

    # ---------- the backend-dependent operations ----------

    def do_arraylen_gc(self, args, arraydescr):
        array = args[0].getptr_base()
        return history.BoxInt(llimpl.do_arraylen_gc(arraydescr, array))

    def do_strlen(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_strlen(0, string))

    def do_strgetitem(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_strgetitem(0, string, index))

    def do_unicodelen(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        return history.BoxInt(llimpl.do_unicodelen(0, string))

    def do_unicodegetitem(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        index = args[1].getint()
        return history.BoxInt(llimpl.do_unicodegetitem(0, string, index))

    def do_getarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, Descr)
        array = args[0].getptr_base()
        index = args[1].getint()
        if arraydescr.typeinfo == 'p':
            return history.BoxPtr(llimpl.do_getarrayitem_gc_ptr(array, index))
        else:
            return history.BoxInt(llimpl.do_getarrayitem_gc_int(array, index,
                                                               self.memo_cast))

    def do_getfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = args[0].getptr_base()
        if fielddescr.typeinfo == 'p':
            return history.BoxPtr(llimpl.do_getfield_gc_ptr(struct,
                                                            fielddescr.ofs))
        else:
            return history.BoxInt(llimpl.do_getfield_gc_int(struct,
                                                            fielddescr.ofs,
                                                            self.memo_cast))
    def do_getfield_raw(self, args, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = self.cast_int_to_adr(args[0].getint())
        if fielddescr.typeinfo == 'p':
            return history.BoxPtr(llimpl.do_getfield_raw_ptr(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))
        else:
            return history.BoxInt(llimpl.do_getfield_raw_int(struct,
                                                             fielddescr.ofs,
                                                             self.memo_cast))

    def do_new(self, args, size):
        assert isinstance(size, Descr)
        return history.BoxPtr(llimpl.do_new(size.ofs))

    def do_new_with_vtable(self, args, descr=None):
        assert descr is None
        vtable = args[0].getint()
        size = self.class_sizes[vtable]
        result = llimpl.do_new(size.ofs)
        llimpl.do_setfield_gc_int(result, self.fielddescrof_vtable.ofs,
                                  vtable, self.memo_cast)
        return history.BoxPtr(result)

    def do_new_array(self, args, size):
        assert isinstance(size, Descr)
        count = args[0].getint()
        return history.BoxPtr(llimpl.do_new_array(size.ofs, count))

    def do_setarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, Descr)
        array = args[0].getptr_base()
        index = args[1].getint()
        if arraydescr.typeinfo == 'p':
            newvalue = args[2].getptr_base()
            llimpl.do_setarrayitem_gc_ptr(array, index, newvalue)
        else:
            newvalue = args[2].getint()
            llimpl.do_setarrayitem_gc_int(array, index, newvalue,
                                          self.memo_cast)

    def do_setfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = args[0].getptr_base()
        if fielddescr.typeinfo == 'p':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_gc_ptr(struct, fielddescr.ofs, newvalue)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_gc_int(struct, fielddescr.ofs, newvalue,
                                      self.memo_cast)

    def do_setfield_raw(self, args, fielddescr):
        assert isinstance(fielddescr, Descr)
        struct = self.cast_int_to_adr(args[0].getint())
        if fielddescr.typeinfo == 'p':
            newvalue = args[1].getptr_base()
            llimpl.do_setfield_raw_ptr(struct, fielddescr.ofs, newvalue,
                                       self.memo_cast)
        else:
            newvalue = args[1].getint()
            llimpl.do_setfield_raw_int(struct, fielddescr.ofs, newvalue,
                                       self.memo_cast)

    def do_same_as(self, args, descr=None):
        return args[0].clonebox()

    def do_newstr(self, args, descr=None):
        assert descr is None
        length = args[0].getint()
        return history.BoxPtr(llimpl.do_newstr(0, length))

    def do_newunicode(self, args, descr=None):
        assert descr is None
        length = args[0].getint()
        return history.BoxPtr(llimpl.do_newunicode(0, length))

    def do_strsetitem(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        index = args[1].getint()
        newvalue = args[2].getint()
        llimpl.do_strsetitem(0, string, index, newvalue)

    def do_unicodesetitem(self, args, descr=None):
        assert descr is None
        string = args[0].getptr_base()
        index = args[1].getint()
        newvalue = args[2].getint()
        llimpl.do_unicodesetitem(0, string, index, newvalue)

    def do_call(self, args, calldescr):
        assert isinstance(calldescr, Descr)
        func = args[0].getint()
        for arg in args[1:]:
            if (isinstance(arg, history.BoxPtr) or
                isinstance(arg, history.ConstPtr)):
                llimpl.do_call_pushptr(arg.getptr_base())
            else:
                llimpl.do_call_pushint(arg.getint())
        if calldescr.typeinfo == 'p':
            return history.BoxPtr(llimpl.do_call_ptr(func, self.memo_cast))
        elif calldescr.typeinfo == 'i':
            return history.BoxInt(llimpl.do_call_int(func, self.memo_cast))
        else:  # calldescr.typeinfo == 'v'  # void
            llimpl.do_call_void(func, self.memo_cast)

    def do_cast_int_to_ptr(self, args, descr=None):
        assert descr is None
        return history.BoxPtr(llimpl.cast_from_int(llmemory.GCREF,
                                                   args[0].getint(),
                                                   self.memo_cast))

    def do_cast_ptr_to_int(self, args, descr=None):
        assert descr is None
        return history.BoxInt(llimpl.cast_to_int(args[0].getptr_base(),
                                                        self.memo_cast))

class OOtypeCPU(BaseCPU):
    is_oo = True

    @staticmethod
    def fielddescrof(T, fieldname):
        # use class where the field is really defined as a key
        T1, _ = T._lookup_field(fieldname)
        return FieldDescr.new(T1, fieldname)

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

    def get_overflow_error(self):
        ll_err = llimpl._get_error(OverflowError)
        return (ootype.cast_to_object(ll_err.args[0]),
                ootype.cast_to_object(ll_err.args[1]))

    def get_zero_division_error(self):
        ll_err = llimpl._get_error(ZeroDivisionError)
        return (ootype.cast_to_object(ll_err.args[0]),
                ootype.cast_to_object(ll_err.args[1]))

    def do_new_with_vtable(self, args, descr=None):
        assert descr is None
        assert len(args) == 1
        cls = args[0].getobj()
        typedescr = self.class_sizes[cls]
        return typedescr.create()

    def do_new_array(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 1
        return typedescr.create_array(args[0])

    def do_new(self, args, typedescr):
        assert isinstance(typedescr, TypeDescr)
        assert len(args) == 0
        return typedescr.create()

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
        self._is_array_of_pointers = (history.getkind(TYPE) == 'obj')

    def is_array_of_pointers(self):
        # for arrays, TYPE is the type of the array item.
        return self._is_array_of_pointers

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
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = getattr(obj, fieldname)
            return boxresult(T, value)
        def setfield(objbox, valuebox):
            obj = ootype.cast_from_object(TYPE, objbox.getobj())
            value = unwrap(T, valuebox)
            setattr(obj, fieldname, value)
            
        self.getfield = getfield
        self.setfield = setfield
        self._is_pointer_field = (history.getkind(T) == 'obj')

    def sort_key(self):
        return self._keys.getkey((self.TYPE, self.fieldname))

    def is_pointer_field(self):
        return self._is_pointer_field

    def equals(self, other):
        return self.TYPE == other.TYPE and \
            self.fieldname == other.fieldname

    def __repr__(self):
        return '<FieldDescr %r>' % self.fieldname


# ____________________________________________________________

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(LLtypeCPU)
pypy.jit.metainterp.executor.make_execute_list(OOtypeCPU)
