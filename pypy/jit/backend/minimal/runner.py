import py
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.debug import ll_assert, debug_print
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.jit.metainterp.history import AbstractDescr, AbstractMethDescr
from pypy.jit.metainterp.history import Box, BoxInt, BoxPtr, BoxObj
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.backend import model
from pypy.jit.backend.llgraph.runner import MethDescr

DEBUG = False

def cached_method(cachename):
    def decorate(func):
        def cached_func(self, *args):
            try:
                return getattr(self, cachename)[args]
            except (KeyError, AttributeError):
                descr = func(self, *args)
                if not hasattr(self, cachename):
                    setattr(self, cachename, {})
                getattr(self, cachename)[args] = descr
                return descr
        return cached_func
    return decorate


class BaseCPU(model.AbstractCPU):

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None):
        self.rtyper = rtyper
        if rtyper:
            if self.is_oo:
                assert rtyper.type_system.name == "ootypesystem"
            else:
                assert rtyper.type_system.name == "lltypesystem"
        self.stats = stats
        self.translate_support_code = translate_support_code
        self._future_values = []
        self._ovf_error_inst = self.setup_error(OverflowError)
        self._zer_error_inst = self.setup_error(ZeroDivisionError)

    def setup_error(self, Class):
        if self.rtyper is not None:   # normal case
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(Class)
            ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)
        else:
            # for tests, a random emulated ll_inst will do
            ll_inst = self._get_fake_inst()
        return self._cast_error_inst(ll_inst)

    def _cast_error_inst(self, ll_inst):
        return ll_inst

    def compile_operations(self, loop):
        pass

    def execute_operations(self, loop):
        valueboxes = self._future_values
        if DEBUG:
            print "execute_operations: starting", loop
            for box in valueboxes:
                print "\t", box, "\t", box.get_()
        self.clear_exception()
        self._guard_failed = False
        while True:
            env = {}
            ll_assert(len(valueboxes) == len(loop.inputargs),
                      "execute_operations: wrong argument count")
            for i in range(len(valueboxes)):
                env[loop.inputargs[i]] = valueboxes[i]
            operations = loop.operations
            i = 0
            #
            while True:
                ll_assert(i < len(operations), "execute_operations: "
                          "reached the end without seeing a final op")
                op = operations[i]
                i += 1
                argboxes = []
                if DEBUG:
                    lst = [' %s ' % opname[op.opnum]]
                for box in op.args:
                    if isinstance(box, Box):
                        box = env[box]
                    argboxes.append(box)
                    if DEBUG:
                        lst.append(str(box.get_()))
                if DEBUG:
                    print ' '.join(lst)
                if op.is_final():
                    break
                if op.is_guard():
                    try:
                        resbox = self.execute_guard(op.opnum, argboxes)
                    except GuardFailed:
                        if DEBUG:
                            print "\t*guard failed (%s)*" % op.getopname()
                        self._guard_failed = True
                        operations = op.suboperations
                        i = 0
                        continue
                else:
                    resbox = executor._execute_nonspec(self, op.opnum,
                                                       argboxes,
                                                       op.descr)
                if op.result is not None:
                    ll_assert(resbox is not None,
                              "execute_operations: unexpectedly got None")
                    if DEBUG:
                        print '\t-->', resbox.get_()
                    env[op.result] = resbox
                else:
                    ll_assert(resbox is None,
                              "execute_operations: unexpectedly got non-None")
            #
            if op.opnum == rop.JUMP:
                loop = op.jump_target
                valueboxes = argboxes
                continue
            if op.opnum == rop.FAIL:
                break
            ll_assert(False, "execute_operations: bad opnum")

        if DEBUG:
            print "execute_operations: leaving", loop
            for box in op.args:
                print "\t", env[box], "\t", env[box].get_()
        self.latest_fail = op, env
        return op

    def set_future_value_int(self, index, intvalue):
        del self._future_values[index:]
        assert len(self._future_values) == index
        self._future_values.append(BoxInt(intvalue))

    def set_future_value_ptr(self, index, ptrvalue):
        del self._future_values[index:]
        assert len(self._future_values) == index
        self._future_values.append(BoxPtr(ptrvalue))

    def set_future_value_obj(self, index, objvalue):
        del self._future_values[index:]
        assert len(self._future_values) == index
        self._future_values.append(BoxObj(objvalue))

    def get_latest_value_int(self, index):
        op, env = self.latest_fail
        return env[op.args[index]].getint()

    def get_latest_value_ptr(self, index):
        op, env = self.latest_fail
        return env[op.args[index]].getptr_base()

    def get_latest_value_obj(self, index):
        op, env = self.latest_fail
        return env[op.args[index]].getobj()
    
    def execute_guard(self, opnum, argboxes):
        if opnum == rop.GUARD_TRUE:
            value = argboxes[0].getint()
            if not value:
                raise GuardFailed
        elif opnum == rop.GUARD_FALSE:
            value = argboxes[0].getint()
            if value:
                raise GuardFailed
        elif opnum == rop.GUARD_CLASS:
            self._execute_guard_class(argboxes)
        elif opnum == rop.GUARD_VALUE:
            value = argboxes[0].getint()
            expected_value = argboxes[1].getint()
            if value != expected_value:
                raise GuardFailed
        elif opnum == rop.GUARD_NONVIRTUALIZED:
            pass    # XXX
        elif opnum == rop.GUARD_NO_EXCEPTION:
            if self.current_exc_inst:
                raise GuardFailed
        elif opnum == rop.GUARD_EXCEPTION:
            return self._execute_guard_exception(argboxes)
        else:
            ll_assert(False, "execute_guard: unknown guard op")

    # ----------

    @cached_method('_fieldcache')
    def fielddescrof(self, T, name):
        TYPE, FIELDTYPE, reveal = self._get_field(T, name)
        dict2 = base_dict.copy()
        dict2['TYPE'] = TYPE
        dict2['reveal'] = reveal
        dict = {'name': name,
                'input': make_reader(FIELDTYPE, 'xbox', dict2),
                'result': make_writer(FIELDTYPE, 'x', dict2),}
        exec py.code.Source("""
            def getfield(cpu, pbox):
                p = reveal(cpu, TYPE, pbox)
                x = getattr(p, %(name)r)
                return %(result)s
            def setfield(cpu, pbox, xbox):
                p = reveal(cpu, TYPE, pbox)
                x = %(input)s
                setattr(p, %(name)r, x)
        """ % dict).compile() in dict2
        sort_key = self._count_sort_key(T, name)
        return FieldDescr(dict2['getfield'], dict2['setfield'], sort_key)

    # ----------

    def do_getfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        assert fielddescr.getfield is not None
        return fielddescr.getfield(self, args[0])

    do_getfield_raw = do_getfield_gc

    def do_setfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        assert fielddescr.setfield is not None
        fielddescr.setfield(self, args[0], args[1])

    do_setfield_raw = do_setfield_gc

    def do_new_array(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        assert arraydescr.new is not None
        p = arraydescr.new(args[0].getint())
        return BoxPtr(p)

    def do_arraylen_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        assert arraydescr.length is not None
        return BoxInt(arraydescr.length(self, args[0]))

    do_arraylen_raw = do_arraylen_gc

    def do_getarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        assert arraydescr.getarrayitem is not None
        index = args[1].getint()
        return arraydescr.getarrayitem(self, args[0], index)
    do_getarrayitem_raw = do_getarrayitem_gc

    def do_setarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        assert arraydescr.setarrayitem is not None
        index = args[1].getint()
        arraydescr.setarrayitem(self, args[0], index, args[2])

    do_setarrayitem_raw = do_setarrayitem_gc

    def do_strlen(self, args, descr=None):
        str = args[0].getptr(lltype.Ptr(rstr.STR))
        return BoxInt(len(str.chars))

    def do_unicodelen(self, args, descr=None):
        unicode = args[0].getptr(lltype.Ptr(rstr.UNICODE))
        return BoxInt(len(unicode.chars))

    def do_call(self, args, calldescr):
        if not we_are_translated():
            py.test.skip("call not supported in non-translated version")
        assert isinstance(calldescr, CallDescr)
        assert calldescr.call is not None
        self.clear_exception()
        func = self._get_func(args[0])
        try:
            box = calldescr.call(self, func, args[1:])
        except Exception, e:
            self.current_exc_inst = self._cast_instance_to_base(e)
            if DEBUG:
                print '\tcall raised!', self.current_exc_inst
            box = calldescr.errbox
            if box:
                box = box.clonebox()
        else:
            if DEBUG:
                print '\tcall did not raise'
        return box


    def set_overflow_error(self):
        self.current_exc_inst = self._ovf_error_inst

    def set_zero_division_error(self):
        self.current_exc_inst = self._zer_error_inst

    def guard_failed(self):
        return self._guard_failed



class LLtypeCPU(BaseCPU):
    is_oo = False

    # ----------------
    # template methods

    def _get_fake_inst(self):
        ll_inst = lltype.malloc(rclass.OBJECT)
        ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                        immortal=True)
        return ll_inst

    def _get_field(self, STRUCT, name):
        PTR = lltype.Ptr(STRUCT)
        FIELDTYPE = getattr(STRUCT, name)
        return PTR, FIELDTYPE, reveal_ptr

    def _count_sort_key(self, STRUCT, name):
        i = list(STRUCT._names).index(name)
        while True:
            _, STRUCT = STRUCT._first_struct()
            if not STRUCT:
                break
            i += len(STRUCT._names) + 1
        return i

    def _get_func(self, funcbox):
        return funcbox.getaddr(self)

    def _cast_instance_to_base(self, e):
        from pypy.rpython.annlowlevel import cast_instance_to_base_ptr
        return cast_instance_to_base_ptr(e)

    def _execute_guard_class(self, argboxes):
        value = argboxes[0].getptr(rclass.OBJECTPTR)
        adr = argboxes[1].getaddr(self)
        expected_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        if value.typeptr != expected_class:
            raise GuardFailed

    def _execute_guard_exception(self, argboxes):
        adr = argboxes[0].getaddr(self)
        expected_class = llmemory.cast_adr_to_ptr(adr, rclass.CLASSTYPE)
        ll_assert(bool(expected_class),
                  "execute_guard: expected_class==NULL")
        exc = self.current_exc_inst
        if exc and rclass.ll_isinstance(exc, expected_class):
            return BoxPtr(self.get_exc_value())
        else:
            raise GuardFailed

    # ----------------

    @cached_method('_sizecache')
    def sizeof(self, TYPE):
        def alloc():
            p = lltype.malloc(TYPE)
            return lltype.cast_opaque_ptr(llmemory.GCREF, p)
        return SizeDescr(alloc)

    @cached_method('_callcache')
    def calldescrof(self, FUNC, ARGS, RESULT):
        dict2 = base_dict.copy()
        args = []
        for i, ARG in enumerate(ARGS):
            args.append(make_reader(ARG, 'args[%d]' % i, dict2))
        dict = {'args': ', '.join(args),
                'result': make_writer(RESULT, 'res', dict2)}
        dict2.update({'rffi': rffi,
                      'FUNC': lltype.Ptr(lltype.FuncType(ARGS, RESULT)),
                      'length': len(ARGS),
                      'll_assert': ll_assert,
                      })
        exec py.code.Source("""
            def call(cpu, function, args):
                ll_assert(len(args) == length, 'call: wrong arg count')
                function = rffi.cast(FUNC, function)
                res = function(%(args)s)
                return %(result)s
        """ % dict).compile() in dict2
        if RESULT is lltype.Void:
            errbox = None
        elif not self.is_oo and isinstance(RESULT, lltype.Ptr) and RESULT.TO._gckind == 'gc':
            errbox = BoxPtr()
        elif self.is_oo and isinstance(RESULT, ootype.OOType):
            errbox = BoxObj()
        else:
            errbox = BoxInt()
        return CallDescr(FUNC, dict2['call'], errbox)


    @cached_method('_arraycache')
    def arraydescrof(self, ARRAY):
        dict2 = base_dict.copy()
        dict2['malloc'] = lltype.malloc
        dict2['ARRAY'] = ARRAY
        dict2['PTR'] = lltype.Ptr(ARRAY)
        dict = {'input': make_reader(ARRAY.OF, 'xbox', dict2),
                'result': make_writer(ARRAY.OF, 'x', dict2)}
        exec py.code.Source("""
            def new(length):
                p = malloc(ARRAY, length)
                return cast_opaque_ptr(GCREF, p)
            def length(cpu, pbox):
                p = reveal_ptr(cpu, PTR, pbox)
                return len(p)
            def getarrayitem(cpu, pbox, index):
                p = reveal_ptr(cpu, PTR, pbox)
                x = p[index]
                return %(result)s
            def setarrayitem(cpu, pbox, index, xbox):
                p = reveal_ptr(cpu, PTR, pbox)
                x = %(input)s
                p[index] = x
        """ % dict).compile() in dict2
        return ArrayDescr(dict2['new'],
                          dict2['length'],
                          dict2['getarrayitem'],
                          dict2['setarrayitem'])

    # ----------
    
    def do_new(self, args, sizedescr):
        assert isinstance(sizedescr, SizeDescr)
        assert sizedescr.alloc is not None
        p = sizedescr.alloc()
        return BoxPtr(p)

    def do_new_with_vtable(self, args, sizedescr):
        assert isinstance(sizedescr, SizeDescr)
        assert sizedescr.alloc is not None
        p = sizedescr.alloc()
        classadr = args[0].getaddr(self)
        pobj = lltype.cast_opaque_ptr(rclass.OBJECTPTR, p)
        pobj.typeptr = llmemory.cast_adr_to_ptr(classadr, rclass.CLASSTYPE)
        return BoxPtr(p)

    def do_newstr(self, args, descr=None):
        p = rstr.mallocstr(args[0].getint())
        return BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))

    def do_newunicode(self, args, descr=None):
        p = rstr.mallocunicode(args[0].getint())
        return BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))

    def do_strgetitem(self, args, descr=None):
        str = args[0].getptr(lltype.Ptr(rstr.STR))
        i = args[1].getint()
        return BoxInt(ord(str.chars[i]))

    def do_unicodegetitem(self, args, descr=None):
        unicode = args[0].getptr(lltype.Ptr(rstr.UNICODE))
        i = args[1].getint()
        return BoxInt(ord(unicode.chars[i]))

    def do_strsetitem(self, args, descr=None):
        str = args[0].getptr(lltype.Ptr(rstr.STR))
        i = args[1].getint()
        str.chars[i] = chr(args[2].getint())

    def do_unicodesetitem(self, args, descr=None):
        unicode = args[0].getptr(lltype.Ptr(rstr.UNICODE))
        i = args[1].getint()
        unicode.chars[i] = unichr(args[2].getint())

    def do_cast_int_to_ptr(self, args, descr=None):
        return BoxPtr(self.cast_int_to_gcref(args[0].getint()))

    def do_cast_ptr_to_int(self, args, descr=None):
        return BoxInt(self.cast_gcref_to_int(args[0].getptr_base()))

    # ----------

    def clear_exception(self):
        self.current_exc_inst = lltype.nullptr(rclass.OBJECT)

    def get_exception(self):
        if self.current_exc_inst:
            return rffi.cast(lltype.Signed, self.current_exc_inst.typeptr)
        else:
            return 0

    def get_exc_value(self):
        return lltype.cast_opaque_ptr(llmemory.GCREF, self.current_exc_inst)

    # ----------

    def cast_gcref_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    def cast_int_to_gcref(self, x):
        return rffi.cast(llmemory.GCREF, x)

    def cast_int_to_adr(self, x):
        return rffi.cast(llmemory.Address, x)

    def cast_adr_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    @specialize.arg(1)
    def cast_int_to_ptr(self, TYPE, x):
        return rffi.cast(TYPE, x)


class OOtypeCPU(BaseCPU):
    is_oo = True

    # ----------------
    # template methods

    def _get_fake_inst(self):
        return ootype.new(ootype.ROOT)
        
    def _get_field(self, TYPE, name):
        _, FIELDTYPE = TYPE._lookup_field(name)
        return TYPE, FIELDTYPE, reveal_obj

    def _count_sort_key(self, TYPE, name):
        try:
            fields = TYPE._allfields()
        except AttributeError:
            fields = TYPE._fields
        fields = sorted(fields.keys())
        return fields.index(name)

    def _cast_error_inst(self, ll_inst):
        return ootype.cast_to_object(ll_inst)

    def _get_func(self, funcbox):
        return funcbox.getobj()

    def _cast_instance_to_base(self, e):
        from pypy.rpython.annlowlevel import cast_instance_to_base_obj
        return ootype.cast_to_object(cast_instance_to_base_obj(e))

    def _execute_guard_class(self, argboxes):
        # XXX: what if we try to cast a List to ROOT?
        value = ootype.cast_from_object(ootype.ROOT, argboxes[0].getobj())
        expected_class = ootype.cast_from_object(ootype.Class, argboxes[1].getobj())
        if ootype.classof(value) != expected_class:
            raise GuardFailed

    def _execute_guard_exception(self, argboxes):
        obj = argboxes[0].getobj()
        expected_class = ootype.cast_from_object(ootype.Class, obj)
        ll_assert(bool(expected_class),
                  "execute_guard: expected_class==NULL")
        exc = ootype.cast_from_object(ootype.ROOT, self.current_exc_inst)
        if exc:
            exc_class = ootype.classof(exc)
            if ootype.subclassof(expected_class, exc_class):
                return BoxObj(self.get_exc_value())
        raise GuardFailed

    # ----------------

    @cached_method('_typedescrcache')
    def typedescrof(self, TYPE):
        def alloc():
            obj = ootype.new(TYPE)
            return ootype.cast_to_object(obj)
        return SizeDescr(alloc)

    @cached_method('_callcache')
    def calldescrof(self, FUNC, ARGS, RESULT):
        from pypy.jit.backend.llgraph.runner import boxresult, make_getargs
        getargs = make_getargs(FUNC.ARGS)
        def call(cpu, funcobj, argboxes):
            func = ootype.cast_from_object(FUNC, funcobj)
            funcargs = getargs(argboxes)
            res = func(*funcargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        if RESULT is lltype.Void:
            errbox = None
        elif not self.is_oo and isinstance(RESULT, lltype.Ptr) and RESULT.TO._gckind == 'gc':
            errbox = BoxPtr()
        elif self.is_oo and isinstance(RESULT, ootype.OOType):
            errbox = BoxObj()
        else:
            errbox = BoxInt()
        return CallDescr(FUNC, call, errbox)

    @cached_method('_arraycache')
    def arraydescrof(self, ARRAY):
        dict2 = base_dict.copy()
        dict2['ootype'] = ootype
        dict2['ARRAY'] = ARRAY
        dict = {'input': make_reader(ARRAY.ITEM, 'xbox', dict2),
                'result': make_writer(ARRAY.ITEM, 'x', dict2)}
        exec py.code.Source("""
            def new(length):
                array = ootype.oonewarray(ARRAY, length)
                return ootype.cast_to_object(array)
            def length(cpu, abox):
                a = ootype.cast_from_object(ARRAY, abox.getobj())
                return a.ll_length()
            def getarrayitem(cpu, abox, index):
                a = ootype.cast_from_object(ARRAY, abox.getobj())
                x = a.ll_getitem_fast(index)
                return %(result)s
            def setarrayitem(cpu, abox, index, xbox):
                a = ootype.cast_from_object(ARRAY, abox.getobj())
                x = %(input)s
                a.ll_setitem_fast(index, x)
        """ % dict).compile() in dict2
        return ArrayDescr(dict2['new'],
                          dict2['length'],
                          dict2['getarrayitem'],
                          dict2['setarrayitem'])


    @cached_method('_methdescrcache')
    def methdescrof(self, SELFTYPE, methname):
        return MethDescr(SELFTYPE, methname)

    # ----------------
    
    def do_new_with_vtable(self, args, sizedescr):
        assert isinstance(sizedescr, SizeDescr)
        assert sizedescr.alloc is not None
        obj = sizedescr.alloc()
        return BoxObj(obj)

    def do_oosend(self, args, descr=None):
        assert isinstance(descr, MethDescr)
        assert descr.callmeth is not None
        selfbox = args[0]
        argboxes = args[1:]
        return descr.callmeth(selfbox, argboxes)

    # ----------
    
    def clear_exception(self):
        self.current_exc_inst = ootype.NULL

    def get_exception(self):
        inst = ootype.cast_from_object(ootype.ROOT, self.current_exc_inst)
        if inst:
            return ootype.cast_to_object(ootype.classof(inst))
        else:
            return ootype.NULL

    def get_exc_value(self):
        return ootype.cast_to_object(self.current_exc_inst)

class SizeDescr(AbstractDescr):
    alloc = None
    def __init__(self, alloc):
        self.alloc = alloc

class FieldDescr(AbstractDescr):
    getfield = None
    setfield = None
    _sort_key = 0
    def __init__(self, getfield, setfield, sort_key):
        self.getfield = getfield
        self.setfield = setfield
        self._sort_key = sort_key
    def sort_key(self):
        return self._sort_key

class ArrayDescr(AbstractDescr):
    new = None
    length = None
    getarrayitem = None
    setarrayitem = None
    def __init__(self, new, length, getarrayitem, setarrayitem):
        self.new = new
        self.length = length
        self.getarrayitem = getarrayitem
        self.setarrayitem = setarrayitem

class CallDescr(AbstractDescr):
    call = None
    errbox = None
    def __init__(self, FUNC, call, errbox):
        self.FUNC = FUNC    # only for debugging
        self.call = call
        self.errbox = errbox


class MethDescr(AbstractMethDescr):
    callmeth = None
    def __init__(self, SELFTYPE, methname):
        from pypy.jit.backend.llgraph.runner import boxresult, make_getargs
        _, meth = SELFTYPE._lookup(methname)
        METH = ootype.typeOf(meth)
        RESULT = METH.RESULT
        getargs = make_getargs(METH.ARGS)
        def callmeth(selfbox, argboxes):
            selfobj = ootype.cast_from_object(SELFTYPE, selfbox.getobj())
            meth = getattr(selfobj, methname)
            methargs = getargs(argboxes)
            res = meth(*methargs)
            if RESULT is not ootype.Void:
                return boxresult(RESULT, res)
        self.callmeth = callmeth


# ____________________________________________________________


def _name(dict, obj):
    name = '_n%d' % len(dict)
    dict[name] = obj
    return name

def make_reader(TYPE, boxstr, dict):
    if TYPE is lltype.Void:
        return "None"
    elif isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return "%s.getptr(%s)" % (boxstr, _name(dict, TYPE))
        else:
            return "cast_adr_to_ptr(%s.getaddr(cpu), %s)" % (boxstr,
                                                             _name(dict, TYPE))
    elif isinstance(TYPE, ootype.OOType):
        return "ootype.cast_from_object(%s, %s.getobj())" % (_name(dict, TYPE), boxstr)
    else:
        return "cast_primitive(%s, %s.getint())" % (_name(dict, TYPE), boxstr)

def make_writer(TYPE, str, dict):
    if TYPE is lltype.Void:
        return "None"
    elif isinstance(TYPE, lltype.Ptr):
        if TYPE.TO._gckind == 'gc':
            return "BoxPtr(cast_opaque_ptr(GCREF, %s))" % (str,)
        else:
            return "BoxInt(rffi.cast(Signed, %s))" % (str,)
    elif isinstance(TYPE, ootype.OOType):
        return "BoxObj(ootype.cast_to_object(%s))" % (str,)
    else:
        return "BoxInt(cast_primitive(Signed, %s))" % (str,)

@specialize.arg(1)
def reveal_ptr(cpu, PTR, box):
    if PTR.TO._gckind == 'gc':
        return box.getptr(PTR)
    else:
        adr = box.getaddr(cpu)
        return llmemory.cast_adr_to_ptr(adr, PTR)

@specialize.arg(1)
def reveal_obj(cpu, TYPE, box):
    if isinstance(TYPE, ootype.OOType):
        return ootype.cast_from_object(TYPE, box.getobj())
    else:
        return lltype.cast_primitive(TYPE, box.getint())

base_dict = {
    'ootype': ootype,
    'cast_primitive': lltype.cast_primitive,
    'cast_adr_to_ptr': llmemory.cast_adr_to_ptr,
    'cast_opaque_ptr': lltype.cast_opaque_ptr,
    'reveal_ptr': reveal_ptr,
    'reveal_obj': reveal_obj,
    'GCREF': llmemory.GCREF,
    'Signed': lltype.Signed,
    'rffi': rffi,
    'BoxInt': BoxInt,
    'BoxPtr': BoxPtr,
    'BoxObj': BoxObj,
    }

class GuardFailed(Exception):
    pass

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(LLtypeCPU)
pypy.jit.metainterp.executor.make_execute_list(OOtypeCPU)
