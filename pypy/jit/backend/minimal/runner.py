import py
from pypy.rlib.objectmodel import specialize
from pypy.rpython.lltypesystem import lltype, llmemory, rffi, rstr, rclass
from pypy.jit.metainterp.history import AbstractDescr, Box, BoxInt, BoxPtr
from pypy.jit.metainterp import executor
from pypy.jit.metainterp.resoperation import rop


class CPU(object):

    def __init__(self, rtyper, stats, translate_support_code=False,
                 mixlevelann=None):
        self.rtyper = rtyper
        self.stats = stats
        self.translate_support_code = translate_support_code
        self.setup()

    def setup(self):
        if self.rtyper is not None:   # normal case
            bk = self.rtyper.annotator.bookkeeper
            clsdef = bk.getuniqueclassdef(OverflowError)
            ovferror_repr = rclass.getclassrepr(self.rtyper, clsdef)
            ll_inst = self.rtyper.exceptiondata.get_standard_ll_exc_instance(
                self.rtyper, clsdef)
        else:
            # for tests, a random emulated ll_inst will do
            ll_inst = lltype.malloc(rclass.OBJECT)
            ll_inst.typeptr = lltype.malloc(rclass.OBJECT_VTABLE,
                                            immortal=True)
        self._ovf_error_vtable = ll_inst.typeptr
        self._ovf_error_inst   = ll_inst

    def compile_operations(self, loop):
        pass

    def execute_operations(self, loop, valueboxes):
        self.clear_exception()
        self._guard_failed = False
        while True:
            env = {}
            assert len(valueboxes) == len(loop.inputargs)
            for i in range(len(valueboxes)):
                env[loop.inputargs[i]] = valueboxes[i]
            operations = loop.operations
            i = 0
            #
            while True:
                assert i < len(operations), ("reached the end without "
                                             "seeing a final op")
                op = operations[i]
                i += 1
                argboxes = []
                for box in op.args:
                    if isinstance(box, Box):
                        box = env[box]
                    argboxes.append(box)
                if op.is_final():
                    break
                if op.is_guard():
                    try:
                        resbox = self.execute_guard(op.opnum, argboxes)
                    except GuardFailed:
                        self._guard_failed = True
                        operations = op.suboperations
                        i = 0
                        continue
                else:
                    resbox = executor._execute_nonspec(self, op.opnum,
                                                       argboxes,
                                                       op.descr)
                if op.result is not None:
                    assert resbox is not None
                    env[op.result] = resbox
                else:
                    assert resbox is None
            #
            if op.opnum == rop.JUMP:
                loop = op.jump_target
                valueboxes = argboxes
                continue
            if op.opnum == rop.FAIL:
                break
            raise 0, "bad opnum"
        #
        for i in range(len(op.args)):
            box = op.args[i]
            if isinstance(box, BoxInt):
                value = env[box].getint()
                box.changevalue_int(value)
            elif isinstance(box, BoxPtr):
                value = env[box].getptr_base()
                box.changevalue_ptr(value)
        return op

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
            value = argboxes[0].getptr(rclass.OBJECTPTR)
            expected_class = self.cast_int_to_ptr(rclass.CLASSTYPE,
                                                  argboxes[1].getint())
            if value.typeptr != expected_class:
                raise GuardFailed
        elif opnum == rop.GUARD_VALUE:
            value = argboxes[0].getint()
            expected_value = argboxes[1].getint()
            if value != expected_value:
                raise GuardFailed
        elif opnum == rop.GUARD_NONVIRTUALIZED:
            pass    # XXX
        elif opnum == rop.GUARD_NO_EXCEPTION:
            if self.current_exception:
                raise GuardFailed
        elif opnum == rop.GUARD_EXCEPTION:
            expected_exception = argboxes[0].getptr(rclass.CLASSTYPE)
            assert expected_exception
            exc = self.current_exception
            if exc and rclass.ll_issubclass(exc, expected_exception):
                raise GuardFailed
        else:
            assert 0, "unknown guard op"

    # ----------

    def sizeof(self, TYPE):
        def alloc():
            p = lltype.malloc(TYPE)
            return lltype.cast_opaque_ptr(llmemory.GCREF, p)
        return SizeDescr(alloc)

    def fielddescrof(self, STRUCT, name):
        dict2 = base_dict.copy()
        dict2['PTR'] = lltype.Ptr(STRUCT)
        FIELDTYPE = getattr(STRUCT, name)
        dict = {'name': name,
                'input': make_reader(FIELDTYPE, 'xbox', dict2),
                'result': make_writer(FIELDTYPE, 'x', dict2)}
        exec py.code.Source("""
            def getfield(p):
                p = cast_opaque_ptr(PTR, p)
                x = getattr(p, %(name)r)
                return %(result)s
            def setfield(p, xbox):
                p = cast_opaque_ptr(PTR, p)
                x = %(input)s
                setattr(p, %(name)r, x)
        """ % dict).compile() in dict2
        sort_key = _count_sort_key(STRUCT, name)
        return FieldDescr(dict2['getfield'], dict2['setfield'], sort_key)

    def calldescrof(self, ARGS, RESULT):
        dict2 = base_dict.copy()
        args = []
        for i, ARG in enumerate(ARGS):
            args.append(make_reader(ARG, 'args[%d]' % i, dict2))
        dict = {'args': ', '.join(args),
                'result': make_writer(RESULT, 'res', dict2)}
        dict2.update({'rffi': rffi,
                      'FUNC': lltype.Ptr(lltype.FuncType(ARGS, RESULT)),
                      'length': len(ARGS),
                      })
        exec py.code.Source("""
            def call(function, args):
                assert len(args) == length
                function = rffi.cast(FUNC, function)
                res = function(%(args)s)
                return %(result)s
        """ % dict).compile() in dict2
        return CallDescr(dict2['call'])

    # ----------

    def do_new(self, args, sizedescr):
        assert isinstance(sizedescr, SizeDescr)
        p = sizedescr.alloc()
        return BoxPtr(p)

    do_new_with_vtable = do_new

    def do_getfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        gcref = args[0].getptr_base()
        return fielddescr.getfield(gcref)

    do_getfield_raw = do_getfield_gc

    def do_setfield_gc(self, args, fielddescr):
        assert isinstance(fielddescr, FieldDescr)
        gcref = args[0].getptr_base()
        fielddescr.setfield(gcref, args[1])

    do_setfield_raw = do_setfield_gc

    def do_new_array(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        p = arraydescr.new(args[0].getint())
        return BoxPtr(p)

    def do_arraylen_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        gcref = args[0].getptr_base()
        return BoxInt(arraydescr.length(gcref))

    do_arraylen_raw = do_arraylen_gc

    def do_getarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        index = args[1].getint()
        gcref = args[0].getptr_base()
        return arraydescr.getarrayitem(gcref, index)
    do_getarrayitem_raw = do_getarrayitem_gc

    def do_setarrayitem_gc(self, args, arraydescr):
        assert isinstance(arraydescr, ArrayDescr)
        index = args[1].getint()
        gcref = args[0].getptr_base()
        arraydescr.setarrayitem(gcref, index, args[2])

    do_setarrayitem_raw = do_setarrayitem_gc

    def do_newstr(self, args, descr=None):
        p = rstr.mallocstr(args[0].getint())
        return BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))

    def do_newunicode(self, args, descr=None):
        p = rstr.mallocunicode(args[0].getint())
        return BoxPtr(lltype.cast_opaque_ptr(llmemory.GCREF, p))

    def do_strlen(self, args, descr=None):
        str = args[0].getptr(lltype.Ptr(rstr.STR))
        return BoxInt(len(str.chars))

    def do_unicodelen(self, args, descr=None):
        unicode = args[0].getptr(lltype.Ptr(rstr.UNICODE))
        return BoxInt(len(unicode.chars))

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

    def do_call(self, args, calldescr):
        self.clear_exception()
        try:
            return calldescr.call(args[0].getint(), args[1:])
        except Exception, e:
            xxx

    # ----------

    def clear_exception(self):
        self.current_exception = lltype.nullptr(rclass.OBJECT_VTABLE)
        self.current_exc_inst = lltype.nullptr(rclass.OBJECT)

    def get_exception(self):
        return rffi.cast(lltype.Signed, self.current_exception)

    def get_exc_value(self):
        return lltype.cast_opaque_ptr(llmemory.GCREF, self.current_exc_inst)

    def set_overflow_error(self):
        self.current_exception = self._ovf_error_vtable
        self.current_exc_inst = self._ovf_error_inst

    def guard_failed(self):
        return self._guard_failed

    # ----------

    def cast_gcref_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    def cast_int_to_gcref(self, x):
        return rffi.cast(llmemory.GCREF, x)

    def cast_adr_to_int(self, x):
        return rffi.cast(lltype.Signed, x)

    @specialize.arg(1)
    def cast_int_to_ptr(self, TYPE, x):
        return rffi.cast(TYPE, x)


class SizeDescr(AbstractDescr):
    def __init__(self, alloc):
        self.alloc = alloc

class FieldDescr(AbstractDescr):
    def __init__(self, getfield, setfield, sort_key):
        self.getfield = getfield
        self.setfield = setfield
        self._sort_key = sort_key
    def sort_key(self):
        return self._sort_key

class CallDescr(AbstractDescr):
    def __init__(self, call):
        self.call = call

# ____________________________________________________________


def _name(dict, obj):
    name = '_n%d' % len(dict)
    dict[name] = obj
    return name

def make_reader(TYPE, boxstr, dict):
    if TYPE is lltype.Void:
        return "None"
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        return "%s.getptr(%s)" % (boxstr, _name(dict, TYPE))
    else:
        return "cast_primitive(%s, %s.getint())" % (_name(dict, TYPE), boxstr)

def make_writer(TYPE, str, dict):
    if TYPE is lltype.Void:
        return "None"
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        return "BoxPtr(cast_opaque_ptr(GCREF, %s))" % (str,)
    else:
        return "BoxInt(cast_primitive(Signed, %s))" % (str,)

def _count_sort_key(STRUCT, name):
    i = list(STRUCT._names).index(name)
    while True:
        _, STRUCT = STRUCT._first_struct()
        if not STRUCT:
            return i
        i += len(STRUCT._names) + 1

base_dict = {
    'cast_primitive': lltype.cast_primitive,
    'cast_opaque_ptr': lltype.cast_opaque_ptr,
    'GCREF': llmemory.GCREF,
    'Signed': lltype.Signed,
    'BoxInt': BoxInt,
    'BoxPtr': BoxPtr,
    }

class GuardFailed(Exception):
    pass

import pypy.jit.metainterp.executor
pypy.jit.metainterp.executor.make_execute_list(CPU)
