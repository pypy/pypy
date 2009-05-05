import py
from pypy.rpython.lltypesystem import lltype, llmemory, rclass
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.llinterp import LLException
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.objectmodel import we_are_translated, r_dict, instantiate
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.debug import debug_print

from pypy.jit.metainterp import history, support, compile
from pypy.jit.metainterp.history import (Const, ConstInt, ConstPtr, Box,
                                         BoxInt, BoxPtr, Options,
                                         ConstObj, BoxObj)
from pypy.jit.metainterp.resoperation import rop
from pypy.jit.metainterp.heaptracker import (get_vtable_for_gcstruct,
                                             populate_type_cache)
from pypy.jit.metainterp import codewriter, executor
from pypy.jit.metainterp import typesystem
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import specialize
from pypy.jit.metainterp.jitprof import Profiler, EmptyProfiler

# ____________________________________________________________

def check_args(*args):
    for arg in args:
        assert isinstance(arg, (Box, Const))

# debug level: 0 off, 1 normal, 2 detailed
DEBUG = 0

def log(msg):
    if not we_are_translated():
        history.log.info(msg)
    elif DEBUG:
        debug_print(msg)

class arguments(object):
    def __init__(self, *argtypes):
        self.argtypes = argtypes

    def __eq__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes == other.argtypes

    def __ne__(self, other):
        if not isinstance(other, arguments):
            return NotImplemented
        return self.argtypes != other.argtypes

    def __call__(self, func, DEBUG=DEBUG):
        argtypes = unrolling_iterable(self.argtypes)
        def wrapped(self, orgpc):
            args = (self, )
            if DEBUG >= 2:
                s = '%s:%d\t%s' % (self.jitcode.name, orgpc, name)
            else:
                s = ''
            for argspec in argtypes:
                if argspec == "box":
                    box = self.load_arg()
                    args += (box, )
                    if DEBUG >= 2:
                        s += '\t' + box.repr_rpython()
                elif argspec == "constbox":
                    args += (self.load_const_arg(), )
                elif argspec == "int":
                    args += (self.load_int(), )
                elif argspec == "jumptarget":
                    args += (self.load_3byte(), )
                elif argspec == "jumptargets":
                    num = self.load_int()
                    args += ([self.load_3byte() for i in range(num)], )
                elif argspec == "bool":
                    args += (self.load_bool(), )
                elif argspec == "2byte":
                    args += (self.load_int(), )
                elif argspec == "varargs":
                    args += (self.load_varargs(), )
                elif argspec == "constargs":
                    args += (self.load_constargs(), )
                elif argspec == "descr":
                    descr = self.load_const_arg()
                    assert isinstance(descr, history.AbstractDescr)
                    args += (descr, )
                elif argspec == "bytecode":
                    bytecode = self.load_const_arg()
                    assert isinstance(bytecode, codewriter.JitCode)
                    args += (bytecode, )
                elif argspec == "orgpc":
                    args += (orgpc, )
                elif argspec == "indirectcallset":
                    indirectcallset = self.load_const_arg()
                    assert isinstance(indirectcallset,
                                      codewriter.IndirectCallset)
                    args += (indirectcallset, )
                elif argspec == "methdescr":
                    methdescr = self.load_const_arg()
                    assert isinstance(methdescr,
                                      history.AbstractMethDescr)
                    args += (methdescr, )
                elif argspec == "virtualizabledesc":
                    from virtualizable import VirtualizableDesc
                    virtualizabledesc = self.load_const_arg()
                    assert isinstance(virtualizabledesc, VirtualizableDesc)
                    args += (virtualizabledesc, )
                else:
                    assert 0, "unknown argtype declaration: %r" % (argspec,)
            if DEBUG >= 2:
                debug_print(s)
            val = func(*args)
            if DEBUG >= 2:
                reprboxes = ' '.join([box.repr_rpython() for box in self.env])
                debug_print('  \x1b[34menv=[%s]\x1b[0m' % (reprboxes,))
            if val is None:
                val = False
            return val
        name = func.func_name
        wrapped.func_name = "wrap_" + name
        wrapped.argspec = self
        return wrapped

# ____________________________________________________________


class MIFrame(object):
    exception_box = None
    exc_value_box = None

    def __init__(self, metainterp, jitcode):
        assert isinstance(jitcode, codewriter.JitCode)
        self.metainterp = metainterp
        self.jitcode = jitcode
        self.bytecode = jitcode.code
        self.constants = jitcode.constants
        self.exception_target = -1
        self.name = jitcode.name # purely for having name attribute

    # ------------------------------
    # Decoding of the JitCode

    def load_int(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        if result > 0x7F:
            result = self._load_larger_int(result)
        return result

    def _load_larger_int(self, result):    # slow path
        result = result & 0x7F
        shift = 7
        pc = self.pc
        while 1:
            byte = ord(self.bytecode[pc])
            pc += 1
            result += (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        self.pc = pc
        return intmask(result)
    _load_larger_int._dont_inline_ = True

    def load_3byte(self):
        pc = self.pc
        result = (((ord(self.bytecode[pc + 0])) << 16) |
                  ((ord(self.bytecode[pc + 1])) <<  8) |
                  ((ord(self.bytecode[pc + 2])) <<  0))
        self.pc = pc + 3
        return result

    def load_bool(self):
        pc = self.pc
        result = ord(self.bytecode[pc])
        self.pc = pc + 1
        return bool(result)

    def getenv(self, i):
        assert i >= 0
        j = i >> 1
        if i & 1:
            return self.constants[j]
        else:
            assert j < len(self.env)
            return self.env[j]

    def load_arg(self):
        return self.getenv(self.load_int())

    def load_const_arg(self):
        return self.constants[self.load_int()]

    def load_varargs(self):
        count = self.load_int()
        return [self.load_arg() for i in range(count)]

    def load_constargs(self):
        count = self.load_int()
        return [self.load_const_arg() for i in range(count)]

    def ignore_varargs(self):
        count = self.load_int()
        for i in range(count):
            self.load_int()

    def getvarenv(self, i):
        return self.env[i]

    def make_result_box(self, box):
        assert isinstance(box, Box) or isinstance(box, Const)
        self.env.append(box)

##    def starts_with_greens(self):
##        green_opcode = self.metainterp._green_opcode
##        if self.bytecode[self.pc] == green_opcode:
##            self.greens = []
##            while self.bytecode[self.pc] == green_opcode:
##                self.pc += 1
##                i = self.load_int()
##                assert isinstance(self.env[i], Const)
##                self.greens.append(i)
##        else:
##            self.greens = None

    # ------------------------------

    for _n in range(codewriter.MAX_MAKE_NEW_VARS):
        _decl = ', '.join(["'box'" for _i in range(_n)])
        _allargs = ', '.join(["box%d" % _i for _i in range(_n)])
        exec py.code.Source("""
            @arguments(%s)
            def opimpl_make_new_vars_%d(self, %s):
                ##self.greens = None
                if not we_are_translated():
                    check_args(%s)
                self.env = [%s]
        """ % (_decl, _n, _allargs, _allargs, _allargs)).compile()

    @arguments("varargs")
    def opimpl_make_new_vars(self, newenv):
        ##self.greens = None
        if not we_are_translated():
            check_args(*newenv)
        self.env = newenv

##    @arguments("int")
##    def opimpl_green(self, green):
##        assert isinstance(self.env[green], Const)
##        if not self.greens:
##            self.greens = []
##        self.greens.append(green)
##        #if not we_are_translated():
##        #    history.log.green(self.env[green])

    for _opimpl in ['int_add', 'int_sub', 'int_mul', 'int_floordiv', 'int_mod',
                    'int_lt', 'int_le', 'int_eq',
                    'int_ne', 'int_gt', 'int_ge',
                    'int_and', 'int_or', 'int_xor',
                    'int_rshift', 'int_lshift', 'uint_rshift',
                    'uint_lt', 'uint_le', 'uint_gt', 'uint_ge',
                    ]:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                self.execute(rop.%s, [b1, b2])
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_add_ovf', 'int_sub_ovf', 'int_mul_ovf', 'int_mod_ovf',
                    'int_lshift_ovf', 'int_floordiv_ovf']:
        exec py.code.Source('''
            @arguments("box", "box")
            def opimpl_%s(self, b1, b2):
                return self.execute_with_exc(rop.%s, [b1, b2])
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_is_true', 'int_neg', 'int_invert', 'bool_not',
                    'cast_ptr_to_int', 'cast_int_to_ptr',
                    'int_abs',
                    ]:
        exec py.code.Source('''
            @arguments("box")
            def opimpl_%s(self, b):
                self.execute(rop.%s, [b])
        ''' % (_opimpl, _opimpl.upper())).compile()

    for _opimpl in ['int_neg_ovf', 'int_abs_ovf',
                    ]:
        exec py.code.Source('''
            @arguments("box")
            def opimpl_%s(self, b):
                return self.execute_with_exc(rop.%s, [b])
        ''' % (_opimpl, _opimpl.upper())).compile()

    @arguments()
    def opimpl_return(self):
        assert len(self.env) == 1
        return self.metainterp.finishframe(self.env[0])

    @arguments()
    def opimpl_void_return(self):
        assert len(self.env) == 0
        return self.metainterp.finishframe(None)

    @arguments("jumptarget")
    def opimpl_goto(self, target):
        self.pc = target

    @arguments("orgpc", "jumptarget", "box", "varargs")
    def opimpl_goto_if_not(self, pc, target, box, livelist):
        switchcase = box.getint()
        if switchcase:
            opnum = rop.GUARD_TRUE
        else:
            self.pc = target
            opnum = rop.GUARD_FALSE
        self.env = livelist
        self.generate_guard(pc, opnum, box)
        # note about handling self.env explicitly here: it is done in
        # such a way that the 'box' on which we generate the guard is
        # typically not included in the livelist.

    def follow_jump(self):
        self.pc += 1          # past the bytecode for 'goto_if_not'
        target = self.load_3byte()  # load the 'target' argument
        self.pc = target      # jump

    def dont_follow_jump(self):
        self.pc += 1          # past the bytecode for 'goto_if_not'
        self.load_3byte()     # past the 'target' argument
        self.load_int()       # past the 'box' argument
        self.ignore_varargs() # past the 'livelist' argument

    @arguments("orgpc", "box", "constargs", "jumptargets")
    def opimpl_switch(self, pc, valuebox, constargs, jumptargets):
        box = self.implement_guard_value(pc, valuebox)
        for i in range(len(constargs)):
            casebox = constargs[i]
            if box.equals(casebox):
                self.pc = jumptargets[i]
                break

    @arguments("orgpc", "box", "constbox")
    def opimpl_switch_dict(self, pc, valuebox, switchdict):
        box = self.implement_guard_value(pc, valuebox)
        search_value = box.getint()
        assert isinstance(switchdict, codewriter.SwitchDict)
        try:
            self.pc = switchdict.dict[search_value]
        except KeyError:
            pass

    @arguments("descr")
    def opimpl_new(self, size):
        self.execute(rop.NEW, [], descr=size)

    @arguments("descr", "constbox")
    def opimpl_new_with_vtable(self, size, vtablebox):
        self.execute(rop.NEW_WITH_VTABLE, [vtablebox], descr=size)

    @arguments("box")
    def opimpl_runtimenew(self, classbox):
        self.execute(rop.RUNTIMENEW, [classbox])

    @arguments("box", "descr")
    def opimpl_instanceof(self, box, typedescr):
        self.execute(rop.INSTANCEOF, [box], descr=typedescr)

    @arguments("descr", "box")
    def opimpl_new_array(self, itemsize, countbox):
        self.execute(rop.NEW_ARRAY, [countbox], descr=itemsize)

    @arguments("box", "descr", "box")
    def opimpl_getarrayitem_gc(self, arraybox, arraydesc, indexbox):
        self.execute(rop.GETARRAYITEM_GC, [arraybox, indexbox],
                     descr=arraydesc)

    @arguments("box", "descr", "box")
    def opimpl_getarrayitem_gc_pure(self, arraybox, arraydesc, indexbox):
        self.execute(rop.GETARRAYITEM_GC_PURE, [arraybox, indexbox],
                     descr=arraydesc)

    @arguments("box", "descr", "box", "box")
    def opimpl_setarrayitem_gc(self, arraybox, arraydesc, indexbox, itembox):
        self.execute(rop.SETARRAYITEM_GC, [arraybox, indexbox, itembox],
                     descr=arraydesc)

    @arguments("box", "descr")
    def opimpl_arraylen_gc(self, arraybox, arraydesc):
        self.execute(rop.ARRAYLEN_GC, [arraybox], descr=arraydesc)

    @arguments("orgpc", "box", "descr", "box")
    def opimpl_check_neg_index(self, pc, arraybox, arraydesc, indexbox):
        negbox = self.metainterp.execute_and_record(
            rop.INT_LT, [indexbox, ConstInt(0)])
        negbox = self.implement_guard_value(pc, negbox)
        if negbox.getint():
            # the index is < 0; add the array length to it
            lenbox = self.metainterp.execute_and_record(
                rop.ARRAYLEN_GC, [arraybox], descr=arraydesc)
            indexbox = self.metainterp.execute_and_record(
                rop.INT_ADD, [indexbox, lenbox])
        self.make_result_box(indexbox)

    @arguments("orgpc", "box")
    def opimpl_check_zerodivisionerror(self, pc, box):
        nonzerobox = self.metainterp.execute_and_record(
            rop.INT_NE, [box, ConstInt(0)])
        nonzerobox = self.implement_guard_value(pc, nonzerobox)
        if nonzerobox.getint():
            return False
        else:
            # division by zero!
            self.metainterp.cpu.set_zero_division_error()
            return self.metainterp.handle_exception()

    @arguments("box")
    def opimpl_ptr_nonzero(self, box):
        self.execute(rop.OONONNULL, [box])

    @arguments("box")
    def opimpl_ptr_iszero(self, box):
        self.execute(rop.OOISNULL, [box])

    @arguments("box")
    def opimpl_oononnull(self, box):
        self.execute(rop.OONONNULL, [box])

    @arguments("box", "box")
    def opimpl_ptr_eq(self, box1, box2):
        self.execute(rop.OOIS, [box1, box2])

    @arguments("box", "box")
    def opimpl_ptr_ne(self, box1, box2):
        self.execute(rop.OOISNOT, [box1, box2])

    opimpl_oois = opimpl_ptr_eq

    @arguments("box", "descr")
    def opimpl_getfield_gc(self, box, fielddesc):
        self.execute(rop.GETFIELD_GC, [box], descr=fielddesc)
    @arguments("box", "descr")
    def opimpl_getfield_gc_pure(self, box, fielddesc):
        self.execute(rop.GETFIELD_GC_PURE, [box], descr=fielddesc)
    @arguments("box", "descr", "box")
    def opimpl_setfield_gc(self, box, fielddesc, valuebox):
        self.execute(rop.SETFIELD_GC, [box, valuebox], descr=fielddesc)

    @arguments("box", "descr")
    def opimpl_getfield_raw(self, box, fielddesc):
        self.execute(rop.GETFIELD_RAW, [box], descr=fielddesc)
    @arguments("box", "descr")
    def opimpl_getfield_raw_pure(self, box, fielddesc):
        self.execute(rop.GETFIELD_RAW_PURE, [box], descr=fielddesc)
    @arguments("box", "descr", "box")
    def opimpl_setfield_raw(self, box, fielddesc, valuebox):
        self.execute(rop.SETFIELD_RAW, [box, valuebox], descr=fielddesc)

    def perform_call(self, jitcode, varargs):
        if (isinstance(self.metainterp.history, history.BlackHole) and
            jitcode.calldescr is not None):
            # when producing only a BlackHole, we can implement this by
            # calling the subfunction directly instead of interpreting it
            if jitcode.cfnptr is not None:
                # for non-oosends
                varargs = [jitcode.cfnptr] + varargs
                return self.execute_with_exc(rop.CALL, varargs,
                                             descr=jitcode.calldescr)
            else:
                # for oosends (ootype only): calldescr is a MethDescr
                return self.execute_with_exc(rop.OOSEND, varargs,
                                             descr=jitcode.calldescr)
        else:
            # when tracing, this bytecode causes the subfunction to be entered
            f = self.metainterp.newframe(jitcode)
            f.setup_call(varargs)
            return True

    @arguments("bytecode", "varargs")
    def opimpl_call(self, callee, varargs):
        return self.perform_call(callee, varargs)

    @arguments("descr", "varargs")
    def opimpl_residual_call(self, calldescr, varargs):
        return self.execute_with_exc(rop.CALL, varargs, descr=calldescr)

    @arguments("descr", "varargs")
    def opimpl_residual_call_noexception(self, calldescr, varargs):
        if not we_are_translated():
            self.metainterp._debug_history.append(['call',
                                                  varargs[0], varargs[1:]])
        self.execute(rop.CALL, varargs, descr=calldescr)

    @arguments("descr", "varargs")
    def opimpl_residual_call_pure(self, calldescr, varargs):
        self.execute(rop.CALL_PURE, varargs, descr=calldescr)

##    @arguments("fixedlist", "box", "box")
##    def opimpl_list_getitem(self, descr, listbox, indexbox):
##        args = [descr.getfunc, listbox, indexbox]
##        return self.execute_with_exc(rop.LIST_GETITEM, args, descr.tp)

##    @arguments("fixedlist", "box", "box", "box")
##    def opimpl_list_setitem(self, descr, listbox, indexbox, newitembox):
##        args = [descr.setfunc, listbox, indexbox, newitembox]
##        return self.execute_with_exc(rop.LIST_SETITEM, args, 'void')

##    @arguments("builtin", "varargs")
##    def opimpl_getitem_foldable(self, descr, varargs):
##        args = [descr.getfunc] + varargs
##        return self.execute_with_exc('getitem', args, descr.tp, True)

##    @arguments("builtin", "varargs")
##    def opimpl_setitem_foldable(self, descr, varargs):
##        args = [descr.setfunc] + varargs
##        return self.execute_with_exc('setitem', args, 'void', True)

##    @arguments("fixedlist", "box", "box")
##    def opimpl_newlist(self, descr, countbox, defaultbox):
##        args = [descr.malloc_func, countbox, defaultbox]
##        return self.execute_with_exc(rop.NEWLIST, args, 'ptr')

##    @arguments("builtin", "varargs")
##    def opimpl_append(self, descr, varargs):
##        args = [descr.append_func] + varargs
##        return self.execute_with_exc('append', args, 'void')

##    @arguments("builtin", "varargs")
##    def opimpl_insert(self, descr, varargs):
##        args = [descr.insert_func] + varargs
##        return self.execute_with_exc('insert', args, 'void')

##    @arguments("builtin", "varargs")
##    def opimpl_pop(self, descr, varargs):
##        args = [descr.pop_func] + varargs
##        return self.execute_with_exc('pop', args, descr.tp)

##    @arguments("builtin", "varargs")
##    def opimpl_len(self, descr, varargs):
##        args = [descr.len_func] + varargs
##        return self.execute_with_exc('len', args, 'int')

##    @arguments("builtin", "varargs")
##    def opimpl_listnonzero(self, descr, varargs):
##        args = [descr.nonzero_func] + varargs
##        return self.execute_with_exc('listnonzero', args, 'int')


    @arguments("orgpc", "indirectcallset", "box", "varargs")
    def opimpl_indirect_call(self, pc, indirectcallset, box, varargs):
        box = self.implement_guard_value(pc, box)
        cpu = self.metainterp.cpu
        if cpu.is_oo:
            key = box.getobj()
        else:
            key = box.getaddr(cpu)
        jitcode = indirectcallset.bytecode_for_address(key)
        f = self.metainterp.newframe(jitcode)
        f.setup_call(varargs)
        return True

    @arguments("orgpc", "methdescr", "varargs")
    def opimpl_oosend(self, pc, methdescr, varargs):
        objbox = varargs[0]
        clsbox = self.cls_of_box(objbox)
        if isinstance(objbox, Box):
            self.generate_guard(pc, rop.GUARD_CLASS, objbox, [clsbox])
        oocls = ootype.cast_from_object(ootype.Class, clsbox.getobj())
        jitcode = methdescr.get_jitcode_for_class(oocls)
        return self.perform_call(jitcode, varargs)

    @arguments("box")
    def opimpl_strlen(self, str):
        self.execute(rop.STRLEN, [str])

    @arguments("box")
    def opimpl_unicodelen(self, str):
        self.execute(rop.UNICODELEN, [str])

    @arguments("box", "box")
    def opimpl_strgetitem(self, str, index):
        self.execute(rop.STRGETITEM, [str, index])

    @arguments("box", "box")
    def opimpl_unicodegetitem(self, str, index):
        self.execute(rop.UNICODEGETITEM, [str, index])

    @arguments("box", "box", "box")
    def opimpl_strsetitem(self, str, index, newchar):
        self.execute(rop.STRSETITEM, [str, index, newchar])

    @arguments("box", "box", "box")
    def opimpl_unicodesetitem(self, str, index, newchar):
        self.execute(rop.UNICODESETITEM, [str, index, newchar])

    @arguments("box")
    def opimpl_newstr(self, length):
        self.execute(rop.NEWSTR, [length])

    @arguments("box")
    def opimpl_newunicode(self, length):
        self.execute(rop.NEWUNICODE, [length])

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_canraise(self, methdescr, varargs):
        return self.execute_with_exc(rop.OOSEND, varargs, descr=methdescr)

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_noraise(self, methdescr, varargs):
        self.execute(rop.OOSEND, varargs, descr=methdescr)

    @arguments("descr", "varargs")
    def opimpl_residual_oosend_pure(self, methdescr, boxes):
        self.execute(rop.OOSEND_PURE, boxes, descr=methdescr)

#    @arguments("box", "box")
#    def opimpl_oostring_char(self, obj, base):
#        self.execute(rop.OOSTRING_CHAR, [obj, base])
#
#    @arguments("box", "box")
#    def opimpl_oounicode_unichar(self, obj, base):
#        self.execute(rop.OOUNICODE_UNICHAR, [obj, base])

    @arguments("orgpc", "box")
    def opimpl_guard_value(self, pc, box):
        constbox = self.implement_guard_value(pc, box)
        self.make_result_box(constbox)

    @arguments("orgpc", "box")
    def opimpl_guard_class(self, pc, box):
        clsbox = self.cls_of_box(box)
        if isinstance(box, Box):
            self.generate_guard(pc, rop.GUARD_CLASS, box, [clsbox])
        self.make_result_box(clsbox)

##    @arguments("orgpc", "box", "builtin")
##    def opimpl_guard_builtin(self, pc, box, builtin):
##        self.generate_guard(pc, "guard_builtin", box, [builtin])

##    @arguments("orgpc", "box", "builtin")
##    def opimpl_guard_len(self, pc, box, builtin):
##        intbox = self.metainterp.cpu.execute_operation(
##            'len', [builtin.len_func, box], 'int')
##        self.generate_guard(pc, "guard_len", box, [intbox])

    @arguments("orgpc", "box", "virtualizabledesc", "descr")
    def opimpl_guard_nonvirtualized(self, pc, box, vdesc, guard_field):
        clsbox = self.cls_of_box(box)
        op = self.generate_guard(pc, rop.GUARD_NONVIRTUALIZED, box,
                                 [clsbox])
        if op:
            op.vdesc = vdesc
            op.setdescr(guard_field)
        
    @arguments("box")
    def opimpl_keepalive(self, box):
        pass     # xxx?

    def generate_merge_point(self, pc, varargs):
        if isinstance(self.metainterp.history, history.BlackHole):
            raise self.metainterp.staticdata.ContinueRunningNormally(varargs)
        num_green_args = self.metainterp.staticdata.num_green_args
        for i in range(num_green_args):
            varargs[i] = self.implement_guard_value(pc, varargs[i])

    @arguments("orgpc")
    def opimpl_can_enter_jit(self, pc):
        # Note: when running with a BlackHole history, this 'can_enter_jit'
        # may be completely skipped by the logic that replaces perform_call
        # with rop.CALL.  But in that case, no-one will check the flag anyway,
        # so it's fine.
        self.metainterp.seen_can_enter_jit = True

    @arguments("orgpc")
    def opimpl_jit_merge_point(self, pc):
        self.generate_merge_point(pc, self.env)
        if self.metainterp.seen_can_enter_jit:
            self.metainterp.seen_can_enter_jit = False
            self.metainterp.reached_can_enter_jit(self.env[:])

    @arguments("jumptarget")
    def opimpl_setup_exception_block(self, exception_target):
        self.exception_target = exception_target

    @arguments()
    def opimpl_teardown_exception_block(self):
        self.exception_target = -1

    @arguments("constbox", "jumptarget")
    def opimpl_goto_if_exception_mismatch(self, vtableref, next_exc_target):
        assert isinstance(self.exception_box, Const)    # XXX
        cpu = self.metainterp.cpu
        ts = self.metainterp.staticdata.ts
        if not ts.subclassOf(cpu, self.exception_box, vtableref):
            self.pc = next_exc_target

    @arguments("int")
    def opimpl_put_last_exception(self, index):
        assert index >= 0
        self.env.insert(index, self.exception_box)

    @arguments("int")
    def opimpl_put_last_exc_value(self, index):
        assert index >= 0
        self.env.insert(index, self.exc_value_box)

    @arguments()
    def opimpl_raise(self):
        assert len(self.env) == 2
        return self.metainterp.finishframe_exception(self.env[0], self.env[1])

    @arguments()
    def opimpl_reraise(self):
        return self.metainterp.finishframe_exception(self.exception_box,
                                                     self.exc_value_box)

    @arguments()
    def opimpl_not_implemented(self):
        raise NotImplementedError

    # ------------------------------

    def setup_call(self, argboxes):
        if not we_are_translated():
            check_args(*argboxes)
        self.pc = 0
        self.env = argboxes
        if not we_are_translated():
            self.metainterp._debug_history[-1][-1] = argboxes
        #self.starts_with_greens()
        #assert len(argboxes) == len(self.graph.getargs())

    def setup_resume_at_op(self, pc, nums, consts, liveboxes,
                           exception_target):
        if not we_are_translated():
            check_args(*liveboxes)
        self.pc = pc
        self.exception_target = exception_target
        self.env = []
        for num in nums:
            if num >= 0:
                box = liveboxes[num]
            else:
                box = consts[~num]
            self.env.append(box)
        if DEBUG >= 2:
            values = ' '.join([box.repr_rpython() for box in self.env])
            log('setup_resume_at_op  %s:%d [%s] %d' % (self.jitcode.name,
                                                       self.pc, values,
                                                       self.exception_target))

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) returns True.  This is the case when the current frame
        # changes, due to a call or a return.
        while True:
            pc = self.pc
            op = ord(self.bytecode[pc])
            #print self.metainterp.opcode_names[op]
            self.pc = pc + 1
            staticdata = self.metainterp.staticdata
            stop = staticdata.opcode_implementations[op](self, pc)
            #self.metainterp.most_recent_mp = None
            if stop:
                break

    def generate_guard(self, pc, opnum, box, extraargs=[]):
        if isinstance(box, Const):    # no need for a guard
            return
        if isinstance(self.metainterp.history, history.BlackHole):
            return
        saved_pc = self.pc
        self.pc = pc
        # XXX 'resume_info' should be shared, either partially or
        #     if possible totally
        resume_info = []
        liveboxes = []
        consts = []
        memo = {}
        for frame in self.metainterp.framestack:
            nums = []
            for framebox in frame.env:
                assert framebox is not None
                if isinstance(framebox, Box):
                    try:
                        num = memo[framebox]
                    except KeyError:
                        num = len(liveboxes)
                        memo[framebox] = num
                        liveboxes.append(framebox)
                else:
                    num = ~len(consts)
                    consts.append(framebox)
                nums.append(num)
            resume_info.append((frame.jitcode, frame.pc, nums,
                                frame.exception_target))
        if box is not None:
            moreargs = [box] + extraargs
        else:
            moreargs = list(extraargs)
        guard_op = self.metainterp.history.record(opnum, moreargs, None)
        resumedescr = compile.ResumeGuardDescr(resume_info, consts,
            self.metainterp.history, len(self.metainterp.history.operations)-1)
        op = history.ResOperation(rop.FAIL, liveboxes, None, descr=resumedescr)
        guard_op.suboperations = [op]
        self.pc = saved_pc
        return guard_op

    def implement_guard_value(self, pc, box):
        if isinstance(box, Box):
            promoted_box = box.constbox()
            self.generate_guard(pc, rop.GUARD_VALUE, box, [promoted_box])
            return promoted_box
        else:
            return box     # no promotion needed, already a Const

    def cls_of_box(self, box):
        return self.metainterp.staticdata.ts.cls_of_box(self.metainterp.cpu, box)

    @specialize.arg(1)
    def execute(self, opnum, argboxes, descr=None):
        resbox = self.metainterp.execute_and_record(opnum, argboxes, descr)
        if resbox is not None:
            self.make_result_box(resbox)

    @specialize.arg(1)
    def execute_with_exc(self, opnum, argboxes, descr=None):
        self.execute(opnum, argboxes, descr)
        if not we_are_translated():
            self.metainterp._debug_history.append(['call',
                                                  argboxes[0], argboxes[1:]])
        return self.metainterp.handle_exception()

# ____________________________________________________________

class MetaInterpStaticData(object):
    num_green_args = 0

    def __init__(self, portal_graph, graphs, cpu, stats, options,
                 optimizer=None, profile=None):
        self.portal_graph = portal_graph
        self.cpu = cpu
        self.stats = stats
        self.options = options
        self.globaldata = MetaInterpGlobalData()

        RESULT = portal_graph.getreturnvar().concretetype
        self.result_type = history.getkind(RESULT)

        self.opcode_implementations = []
        self.opcode_names = []
        self.opname_to_index = {}
        self._class_sizes = populate_type_cache(graphs, self.cpu)
        if not cpu.translate_support_code:
            self.cpu.class_sizes = self._class_sizes
        else:
            self.cpu.class_sizes = None
        self._virtualizabledescs = {}
        if optimizer is not None:
            self.optimize_loop = optimizer.optimize_loop
            self.optimize_bridge = optimizer.optimize_bridge
        else:
            from pypy.jit.metainterp import optimize
            self.optimize_loop = optimize.optimize_loop
            self.optimize_bridge = optimize.optimize_bridge

        if self.cpu.is_oo:
            self.ts = typesystem.oohelper
        else:
            self.ts = typesystem.llhelper

        if profile is not None:
            self.profiler = profile()
        else:
            self.profiler = EmptyProfiler()

    def _freeze_(self):
        return True

    def _setup_once(self):
        """Runtime setup needed by the various components of the JIT."""
        if not self.globaldata.initialized:
            if self.cpu.class_sizes is None:
                cs = {}
                for key, value in self._class_sizes:
                    cs[key] = value
                self.cpu.class_sizes = cs
            self.cpu.setup_once()
            if not self.profiler.initialized:
                self.profiler.start()
                self.profiler.initialized = True
            self.globaldata.initialized = True

    def generate_bytecode(self, policy, ts):
        self._codewriter = codewriter.CodeWriter(self, policy, ts)
        self.portal_code = self._codewriter.make_portal_bytecode(
            self.portal_graph)

    # ---------- construction-time interface ----------

    def _register_opcode(self, opname):
        assert len(self.opcode_implementations) < 256, \
               "too many implementations of opcodes!"
        name = "opimpl_" + opname
        self.opname_to_index[opname] = len(self.opcode_implementations)
        self.opcode_names.append(opname)
        self.opcode_implementations.append(getattr(MIFrame, name).im_func)

    def find_opcode(self, name):
        try:
            return self.opname_to_index[name]
        except KeyError:
            self._register_opcode(name)
            return self.opname_to_index[name]

# ____________________________________________________________

class MetaInterpGlobalData(object):
    def __init__(self):
        self._debug_history = []
        self.compiled_merge_points = r_dict(history.mp_eq, history.mp_hash)
                 # { greenkey: list-of-MergePoints }
        self.initialized = False

# ____________________________________________________________

class MetaInterp(object):
    def __init__(self, staticdata):
        self.staticdata = staticdata
        self.cpu = staticdata.cpu
        if not we_are_translated():
            self._debug_history = staticdata.globaldata._debug_history

    def newframe(self, jitcode):
        if not we_are_translated():
            self._debug_history.append(['enter', jitcode, None])
        f = MIFrame(self, jitcode)
        self.framestack.append(f)
        return f

    def finishframe(self, resultbox):
        frame = self.framestack.pop()
        if not we_are_translated():
            self._debug_history.append(['leave', frame.jitcode, None])
        if self.framestack:
            if resultbox is not None:
                self.framestack[-1].make_result_box(resultbox)
            return True
        else:
            if not isinstance(self.history, history.BlackHole):
                self.compile_done_with_this_frame(resultbox)
            sd = self.staticdata
            if sd.result_type == 'void':
                assert resultbox is None
                raise sd.DoneWithThisFrameVoid()
            elif sd.result_type == 'int':
                raise sd.DoneWithThisFrameInt(resultbox.getint())
            elif sd.result_type == 'ptr':
                raise sd.DoneWithThisFramePtr(resultbox.getptr_base())
            elif self.cpu.is_oo and sd.result_type == 'obj':
                raise sd.DoneWithThisFrameObj(resultbox.getobj())
            else:
                assert False

    def finishframe_exception(self, exceptionbox, excvaluebox):
        # detect and propagate some exceptions early:
        #  - AssertionError
        #  - all subclasses of JitException
        if we_are_translated():
            from pypy.jit.metainterp.warmspot import JitException
            e = self.staticdata.ts.get_exception_obj(excvaluebox)
            if isinstance(e, JitException) or isinstance(e, AssertionError):
                raise Exception, e
        #
        while self.framestack:
            frame = self.framestack[-1]
            if frame.exception_target >= 0:
                frame.pc = frame.exception_target
                frame.exception_target = -1
                frame.exception_box = exceptionbox
                frame.exc_value_box = excvaluebox
                return True
            if not we_are_translated():
                self._debug_history.append(['leave_exc', frame.jitcode, None])
            self.framestack.pop()
        if not isinstance(self.history, history.BlackHole):
            self.compile_exit_frame_with_exception(excvaluebox)
        if self.cpu.is_oo:
            raise self.staticdata.ExitFrameWithExceptionObj(excvaluebox.getobj())
        else:
            raise self.staticdata.ExitFrameWithExceptionPtr(excvaluebox.getptr_base())

    def create_empty_history(self):
        self.history = history.History(self.cpu)
        if self.staticdata.stats is not None:
            self.staticdata.stats.history = self.history

    def _all_constants(self, boxes):
        for box in boxes:
            if not isinstance(box, Const):
                return False
        return True

    @specialize.arg(1)
    def execute_and_record(self, opnum, argboxes, descr=None):
        # execute the operation first
        history.check_descr(descr)
        resbox = executor.execute(self.cpu, opnum, argboxes, descr)
        # check if the operation can be constant-folded away
        canfold = False
        if rop._ALWAYS_PURE_FIRST <= opnum <= rop._ALWAYS_PURE_LAST:
            # this part disappears if execute() is specialized for an
            # opnum that is not within the range
            canfold = self._all_constants(argboxes)
            if canfold:
                resbox = resbox.constbox()       # ensure it is a Const
            else:
                resbox = resbox.nonconstbox()    # ensure it is a Box
        else:
            assert resbox is None or isinstance(resbox, Box)
        # record the operation if not constant-folded away
        if not canfold:
            self.history.record(opnum, argboxes, resbox, descr)
        return resbox

    def _interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ContinueRunningNormally, or a GenerateMergePoint exception.
        if not we_are_translated():
            history.log.event('ENTER' + self.history.extratext)
            self.staticdata.stats.enter_count += 1
        elif DEBUG:
            debug_print('~~~ ENTER', self.history.extratext)
        try:
            while True:
                self.framestack[-1].run_one_step()
        finally:
            if isinstance(self.history, history.BlackHole):
                self.staticdata.profiler.end_blackhole()
            else:
                self.staticdata.profiler.end_tracing()
            if not we_are_translated():
                history.log.event('LEAVE' + self.history.extratext)
            elif DEBUG:
                debug_print('~~~ LEAVE', self.history.extratext)

    def interpret(self):
        if we_are_translated():
            self._interpret()
        else:
            try:
                self._interpret()
            except:
                import sys
                if sys.exc_info()[0] is not None:
                    history.log.info(sys.exc_info()[0].__name__)
                raise

    def compile_and_run_once(self, *args):
        log('Switching from interpreter to compiler')
        original_boxes = self.initialize_state_from_start(*args)
        self.current_merge_points = [(original_boxes, 0)]
        self.resumekey = compile.ResumeFromInterpDescr(original_boxes)
        self.extra_rebuild_operations = -1
        self.seen_can_enter_jit = False
        try:
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            return self.designate_target_loop(gmp)

    def handle_guard_failure(self, exec_result, key):
        self.initialize_state_from_guard_failure(exec_result)
        assert isinstance(key, compile.ResumeGuardDescr)
        top_history = key.find_toplevel_history()
        source_loop = top_history.source_link
        assert isinstance(source_loop, history.TreeLoop)
        original_boxes = source_loop.greenkey + top_history.inputargs
        self.current_merge_points = [(original_boxes, 0)]
        self.resumekey = key
        self.seen_can_enter_jit = False
        guard_op = key.get_guard_op()
        try:
            self.prepare_resume_from_failure(guard_op.opnum)
            self.interpret()
            assert False, "should always raise"
        except GenerateMergePoint, gmp:
            return self.designate_target_loop(gmp)

    def reached_can_enter_jit(self, live_arg_boxes):
        # Called whenever we reach the 'can_enter_jit' hint.
        # First, attempt to make a bridge:
        # - if self.resumekey is a ResumeGuardDescr, it starts from a guard
        #   that failed;
        # - if self.resumekey is a ResumeFromInterpDescr, it starts directly
        #   from the interpreter.
        self.compile_bridge(live_arg_boxes)
        # raises in case it works -- which is the common case, hopefully,
        # at least for bridges starting from a guard.

        # Search in current_merge_points for original_boxes with compatible
        # green keys, representing the beginning of the same loop as the one
        # we end now. 
       
        for j in range(len(self.current_merge_points)-1, -1, -1):
            original_boxes, start = self.current_merge_points[j]
            assert len(original_boxes) == len(live_arg_boxes)
            for i in range(self.staticdata.num_green_args):
                box1 = original_boxes[i]
                box2 = live_arg_boxes[i]
                if not box1.equals(box2):
                    break
            else:
                # Found!  Compile it as a loop.
                if j > 0:
                    pass
                elif self.extra_rebuild_operations >= 0:
                    # The history only starts at a bridge, not at the
                    # full loop header.  Complete it as a full loop by
                    # inserting a copy of the operations from the old
                    # loop branch before the guard that failed.
                    lgt = self.extra_rebuild_operations
                    assert lgt >= 0
                    del self.history.operations[:lgt]
                    compile.prepare_loop_from_bridge(self, self.resumekey)
                loop = self.compile(original_boxes, live_arg_boxes, start)
                raise GenerateMergePoint(live_arg_boxes, loop)

        # Otherwise, no loop found so far, so continue tracing.
        start = len(self.history.operations)
        self.current_merge_points.append((live_arg_boxes, start))

    def resume_already_compiled(self, live_arg_boxes):
        log('followed a path already compiled earlier')
        key = self.resumekey
        assert isinstance(key, compile.ResumeGuardDescr)
        guard_op = key.get_guard_op()
        loop = guard_op.suboperations[-1].jump_target
        raise GenerateMergePoint(live_arg_boxes, loop)

    def designate_target_loop(self, gmp):
        loop = gmp.target_loop
        num_green_args = self.staticdata.num_green_args
        residual_args = self.get_residual_args(loop,
                                               gmp.argboxes[num_green_args:])
        history.set_future_values(self.cpu, residual_args)
        return loop

    def prepare_resume_from_failure(self, opnum):
        if opnum == rop.GUARD_TRUE:     # a goto_if_not that jumps only now
            self.framestack[-1].follow_jump()
        elif opnum == rop.GUARD_FALSE:     # a goto_if_not that stops jumping
            self.framestack[-1].dont_follow_jump()
        elif opnum == rop.GUARD_NO_EXCEPTION or opnum == rop.GUARD_EXCEPTION:
            self.handle_exception()

    def compile(self, original_boxes, live_arg_boxes, start):
        num_green_args = self.staticdata.num_green_args
        self.history.inputargs = original_boxes[num_green_args:]
        greenkey = original_boxes[:num_green_args]
        glob = self.staticdata.globaldata
        old_loops = glob.compiled_merge_points.setdefault(greenkey, [])
        self.history.record(rop.JUMP, live_arg_boxes[num_green_args:], None)
        loop = compile.compile_new_loop(self, old_loops, greenkey, start)
        assert loop is not None
        if not we_are_translated():
            loop._call_history = self._debug_history
        return loop

    def compile_bridge(self, live_arg_boxes):
        num_green_args = self.staticdata.num_green_args
        greenkey = live_arg_boxes[:num_green_args]
        glob = self.staticdata.globaldata
        try:
            old_loops = glob.compiled_merge_points[greenkey]
        except KeyError:
            return
        self.history.record(rop.JUMP, live_arg_boxes[num_green_args:], None)
        target_loop = compile.compile_new_bridge(self, old_loops,
                                                 self.resumekey)
        if target_loop is not None:   # raise if it *worked* correctly
            raise GenerateMergePoint(live_arg_boxes, target_loop)
        self.history.operations.pop()     # remove the JUMP

    def compile_done_with_this_frame(self, exitbox):
        # temporarily put a JUMP to a pseudo-loop
        sd = self.staticdata
        if sd.result_type == 'void':
            assert exitbox is None
            exits = []
            loops = compile.loops_done_with_this_frame_void
        elif sd.result_type == 'int':
            exits = [exitbox]
            loops = compile.loops_done_with_this_frame_int
        elif sd.result_type == 'ptr':
            exits = [exitbox]
            loops = compile.loops_done_with_this_frame_ptr
        elif sd.cpu.is_oo and sd.result_type == 'obj':
            exits = [exitbox]
            loops = compile.loops_done_with_this_frame_obj
        else:
            assert False
        self.history.record(rop.JUMP, exits, None)
        target_loop = compile.compile_new_bridge(self, loops, self.resumekey)
        assert target_loop is loops[0]

    def compile_exit_frame_with_exception(self, valuebox):
        # temporarily put a JUMP to a pseudo-loop
        self.history.record(rop.JUMP, [valuebox], None)
        if self.cpu.is_oo:
            loops = compile.loops_exit_frame_with_exception_obj
        else:
            loops = compile.loops_exit_frame_with_exception_ptr
        target_loop = compile.compile_new_bridge(self, loops, self.resumekey)
        assert target_loop is loops[0]

    def get_residual_args(self, loop, args):
        if loop.specnodes is None:     # it is None only for tests
            return args
        assert len(loop.specnodes) == len(args)
        expanded_args = []
        for i in range(len(loop.specnodes)):
            specnode = loop.specnodes[i]
            specnode.extract_runtime_data(self.cpu, args[i], expanded_args)
        return expanded_args

    def _initialize_from_start(self, original_boxes, num_green_args, *args):
        if args:
            value = args[0]
            if isinstance(lltype.typeOf(value), lltype.Ptr):
                if lltype.typeOf(value).TO._gckind == 'gc':
                    value = lltype.cast_opaque_ptr(llmemory.GCREF, value)
                    if num_green_args > 0:
                        cls = ConstPtr
                    else:
                        cls = BoxPtr
                else:
                    adr = llmemory.cast_ptr_to_adr(value)
                    value = self.cpu.cast_adr_to_int(adr)
                    if num_green_args > 0:
                        cls = ConstInt
                    else:
                        cls = BoxInt
            elif isinstance(lltype.typeOf(value), ootype.OOType):
                value = ootype.cast_to_object(value)
                if num_green_args > 0:
                    cls = ConstObj
                else:
                    cls = BoxObj
            else:
                if num_green_args > 0:
                    cls = ConstInt
                else:
                    cls = BoxInt
                value = intmask(value)
            box = cls(value)
            original_boxes.append(box)
            self._initialize_from_start(original_boxes, num_green_args-1,
                                        *args[1:])

    def initialize_state_from_start(self, *args):
        self.staticdata._setup_once()
        self.staticdata.profiler.start_tracing()
        self.create_empty_history()
        num_green_args = self.staticdata.num_green_args
        original_boxes = []
        self._initialize_from_start(original_boxes, num_green_args, *args)
        # ----- make a new frame -----
        self.framestack = []
        f = self.newframe(self.staticdata.portal_code)
        f.pc = 0
        f.env = original_boxes[:]
        return original_boxes

    def initialize_state_from_guard_failure(self, guard_failure):
        # guard failure: rebuild a complete MIFrame stack
        resumedescr = guard_failure.descr
        assert isinstance(resumedescr, compile.ResumeGuardDescr)
        warmrunnerstate = self.staticdata.state
        must_compile = warmrunnerstate.must_compile_from_failure(resumedescr)
        if must_compile:
            guard_op = resumedescr.get_guard_op()
            suboperations = guard_op.suboperations
            if suboperations[-1].opnum != rop.FAIL:
                must_compile = False
                log("ignoring old version of the guard")
            else:
                self.history = history.History(self.cpu)
                extra = len(suboperations) - 1
                assert extra >= 0
                for i in range(extra):
                    self.history.operations.append(suboperations[i])
                self.extra_rebuild_operations = extra
        if must_compile:
            self.staticdata.profiler.start_tracing()
        else:
            self.staticdata.profiler.start_blackhole()
            self.history = history.BlackHole(self.cpu)
            # the BlackHole is invalid because it doesn't start with
            # guard_failure.key.guard_op.suboperations, but that's fine
        self.rebuild_state_after_failure(resumedescr.resume_info,
                                         resumedescr.consts,
                                         guard_failure.args)

    def handle_exception(self):
        etype = self.cpu.get_exception()
        evalue = self.cpu.get_exc_value()
        self.cpu.clear_exception()
        frame = self.framestack[-1]
        if etype:
            exception_box = self.staticdata.ts.get_exception_box(etype)
            exc_value_box = self.staticdata.ts.get_exc_value_box(evalue)
            op = frame.generate_guard(frame.pc, rop.GUARD_EXCEPTION,
                                      None, [exception_box])
            if op:
                op.result = exc_value_box
            return self.finishframe_exception(exception_box, exc_value_box)
        else:
            frame.generate_guard(frame.pc, rop.GUARD_NO_EXCEPTION, None, [])
            return False

    def rebuild_state_after_failure(self, resume_info, consts, newboxes):
        if not we_are_translated():
            self._debug_history.append(['guard_failure', None, None])
        self.framestack = []
        for jitcode, pc, nums, exception_target in resume_info:
            f = self.newframe(jitcode)
            f.setup_resume_at_op(pc, nums, consts, newboxes,
                                           exception_target)

class GenerateMergePoint(Exception):
    def __init__(self, args, target_loop):
        assert target_loop is not None
        self.argboxes = args
        self.target_loop = target_loop
