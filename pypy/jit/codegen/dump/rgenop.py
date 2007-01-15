"""
This backend records all operations that the JIT front-end tries to do,
and writes them as pseudo-Python source in

    /tmp/usession-<yourname>/rdumpgenop.py.
"""
import os
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import AbstractRGenOp, GenLabel, GenBuilder
from pypy.jit.codegen.model import GenVar, GenConst, CodeGenSwitch
from pypy.tool.udir import udir

LOGFILE = str(udir.join('rdumpgenop.py'))


class FinishedGeneratingCannotExecute(Exception):
    pass


class Label(GenLabel):
    def __init__(self, name):
        self.name = name

class Var(GenVar):
    def __init__(self, name):
        self.name = name

class DummyConst(GenConst):
    def __init__(self, name):
        self.name = name
    @specialize.arg(1)
    def revealconst(self, T):
        raise FinishedGeneratingCannotExecute

class IntConst(GenConst):
    def __init__(self, value):
        self.value = value
        self.name = 'rgenop.genconst(%d)' % value

    @specialize.arg(1)
    def revealconst(self, T):
        if isinstance(T, lltype.Ptr):
            return lltype.cast_int_to_ptr(T, self.value)
        elif T is llmemory.Address:
            return llmemory.cast_int_to_adr(self.value)
        else:
            return lltype.cast_primitive(T, self.value)

class AddrConst(GenConst):
    def __init__(self, addr):
        self.addr = addr
        if we_are_translated():
            intaddr = llmemory.cast_adr_to_int(self.addr)
            self.name = '<address %s>' % intaddr
        else:
            self.name = repr(addr)

    @specialize.arg(1)
    def revealconst(self, T):
        if T is llmemory.Address:
            return self.addr
        elif isinstance(T, lltype.Ptr):
            return llmemory.cast_adr_to_ptr(self.addr, T)
        elif T is lltype.Signed:
            return llmemory.cast_adr_to_int(self.addr)
        else:
            assert 0, "XXX not implemented"


class FlexSwitch(CodeGenSwitch):
    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.name = rgenop.count('flexswitch')
        self.dump = rgenop.dump

    def add_case(self, gv_case):
        builder = Builder(self.rgenop)
        self.dump("%s = %s.add_case(%s)" % (builder.name,
                                            self.name,
                                            gv_case.name))
        return builder


class Builder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop
        self.name = rgenop.count('builder')
        self.dump = rgenop.dump

    def start_writing(self):
        self.dump("%s.start_writing()" % self.name)

    def enter_next_block(self, kinds, args_gv):
        lbl = Label(self.rgenop.count('label'))
        copies_gv = [Var(self.rgenop.count('v')) for v in args_gv]
        self.dump("args_gv = [%s]" % ', '.join([v.name for v in args_gv]))
        self.dump("%s = %s.enter_next_block([%s], args_gv)" % (
            lbl.name,
            self.name,
            ', '.join(kinds)))
        self.dump("[%s] = args_gv" % ', '.join([v.name for v in copies_gv]))
        args_gv[:len(copies_gv)] = copies_gv
        return lbl

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        b = Builder(self.rgenop)
        self.dump("%s = %s.jump_if_false(%s, [%s])" % (
            b.name,
            self.name,
            gv_condition.name,
            ', '.join([v.name for v in args_for_jump_gv])))
        return b

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        b = Builder(self.rgenop)
        self.dump("%s = %s.jump_if_true(%s, [%s])" % (
            b.name,
            self.name,
            gv_condition.name,
            ', '.join([v.name for v in args_for_jump_gv])))
        return b

    def finish_and_goto(self, outputargs_gv, targetlbl):
        self.dump("%s.finish_and_goto([%s], %s)" % (
            self.name,
            ', '.join([v.name for v in outputargs_gv]),
            targetlbl.name))

    def finish_and_return(self, sigtoken, gv_returnvar):
        self.dump("%s.finish_and_return(%s, %s)" % (self.name,
                                                    sigtoken,
                                                    gv_returnvar.name))

    def pause_writing(self, alive_gv):
        b = Builder(self.rgenop)
        self.dump("%s = %s.pause_writing([%s])" % (
            b.name,
            self.name,
            ', '.join([v.name for v in alive_gv])))
        return b

    def end(self):
        self.dump("%s.end()" % (self.name,))

    def genop1(self, opname, gv_arg):
        v = Var(self.rgenop.count("v" + opname))
        self.dump("%s = %s.genop1('%s', %s)" % (v.name, self.name,
                                                opname, gv_arg.name))
        return v

    def genop2(self, opname, gv_arg1, gv_arg2):
        v = Var(self.rgenop.count("v" + opname))
        self.dump("%s = %s.genop2('%s', %s, %s)" % (v.name, self.name, opname,
                                                   gv_arg1.name, gv_arg2.name))
        return v

    def genop_same_as(self, kind, gv_x):
        v = Var(self.rgenop.count("v"))
        self.dump("%s = %s.genop_same_as(%s, %s)" % (v.name, self.name,
                                                     kind, gv_x.name))
        return v

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        v = Var(self.rgenop.count("vcall"))
        self.dump("%s = %s.genop_call(%s, %s, [%s])" % (
            v.name,
            self.name,
            sigtoken,
            gv_fnptr.name,
            ', '.join([v.name for v in args_gv])))
        return v

    def genop_malloc_fixedsize(self, size):
        v = Var(self.rgenop.count("vmalloc"))
        self.dump("%s = %s.genop_malloc_fixedsize(%s)" % (v.name,
                                                          self.name,
                                                          size))
        return v

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        v = Var(self.rgenop.count("vmalloc"))
        self.dump("%s = %s.genop_malloc_varsize(%s, %s)" % (v.name,
                                                            self.name,
                                                            varsizealloctoken,
                                                            gv_size.name))
        return v

    def genop_getfield(self, fieldtoken, gv_ptr):
        v = Var(self.rgenop.count("vget"))
        self.dump("%s = %s.genop_getfield(%s, %s)" % (v.name,
                                                      self.name,
                                                      fieldtoken,
                                                      gv_ptr.name))
        return v

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        self.dump("%s.genop_setfield(%s, %s, %s)" % (self.name,
                                                     fieldtoken,
                                                     gv_ptr.name,
                                                     gv_value.name))

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        v = Var(self.rgenop.count("vsubstruct"))
        self.dump("%s = %s.genop_getsubstruct(%s, %s)" % (v.name,
                                                          self.name,
                                                          fieldtoken,
                                                          gv_ptr.name))
        return v

    def genop_getarrayitem(self, arraytoken, gv_array, gv_index):
        v = Var(self.rgenop.count("vitem"))
        self.dump("%s = %s.genop_getarrayitem(%s, %s, %s)" % (v.name,
                                                              self.name,
                                                              arraytoken,
                                                              gv_array.name,
                                                              gv_index.name))
        return v

    def genop_setarrayitem(self, arraytoken, gv_array, gv_index, gv_value):
        self.dump("%s.genop_setarrayitem(%s, %s, %s, %s)" % (self.name,
                                                             gv_array.name,
                                                             gv_index.name,
                                                             gv_value.name))

    def genop_getarraysubstruct(self, arraytoken, gv_array, gv_index):
        v = Var(self.rgenop.count("vsubitem"))
        self.dump("%s = %s.genop_getarraysubstruct(%s, %s, %s)" % (
            v.name,
            self.name,
            arraytoken,
            gv_array.name,
            gv_index.name))
        return v

    def genop_getarraysize(self, arraytoken, gv_array):
        v = Var(self.rgenop.count("vlen"))
        self.dump("%s = %s.genop_getarraysubstruct(%s, %s)" % (
            v.name,
            self.name,
            arraytoken,
            gv_array.name))
        return v

    def flexswitch(self, gv_exitswitch, args_gv):
        result = FlexSwitch(self.rgenop)
        default_builder = Builder(self.rgenop)
        self.dump("%s, %s = %s.flexswitch(%s, [%s])" % (
            result.name,
            default_builder.name,
            self.name,
            gv_exitswitch.name,
            ', '.join([v.name for v in args_gv])))
        return result, default_builder

    def show_incremental_progress(self):
        pass

    def log(self, msg):
        self.rgenop.dump('# log: %s' % (msg,))


class RDumpGenOp(AbstractRGenOp):
    create_dump = True

    def __init__(self):
        self.keepalive_gc_refs = []
        self.counters = {}
        if self.create_dump:
            self.dump("# ------------------------------------------------------------")

    def count(self, prefix):
        count = self.counters.get(prefix, 0)
        self.counters[prefix] = count + 1
        return '%s%d' % (prefix, count)

    def dump(self, text):
        print text
        text += '\n'
        fd = os.open(LOGFILE, os.O_WRONLY|os.O_CREAT, 0666)
        os.lseek(fd, 0, 2)
        while text:
            count = os.write(fd, text)
            if count == 0:
                raise IOError
            text = text[count:]
        os.close(fd)

    def check_no_open_mc(self):
        pass

    def newgraph(self, sigtoken, name):
        numargs = sigtoken
        inputargs_gv = [Var("gv_%s_inputarg%d" % (name, i))
                        for i in range(numargs)]
        builder = Builder(self)
        self.dump("%s, gv_graph, [%s] = newgraph(%s, '%s')" % (
            builder.name,
            ', '.join([v.name for v in inputargs_gv]),
            sigtoken, name))
        v = DummyConst("graph " + name)
        return builder, v, inputargs_gv

    @specialize.genconst(1)
    def genconst(self, llvalue):
        T = lltype.typeOf(llvalue)
        if T is llmemory.Address:
            return AddrConst(llvalue)
        elif isinstance(T, lltype.Primitive):
            return IntConst(lltype.cast_primitive(lltype.Signed, llvalue))
        elif isinstance(T, lltype.Ptr):
            lladdr = llmemory.cast_ptr_to_adr(llvalue)
            if T.TO._gckind == 'gc':
                self.keepalive_gc_refs.append(lltype.cast_opaque_ptr(llmemory.GCREF, llvalue))
            return AddrConst(lladdr)
        else:
            assert 0, "XXX not implemented"

    @staticmethod
    @specialize.memo()
    def fieldToken(T, name):
        return "field %r of %s %r" % (name, T.__class__.__name__, T._name)

    @staticmethod
    @specialize.memo()
    def allocToken(T):
        return str(T)

    varsizeAllocToken = allocToken

    @staticmethod
    @specialize.memo()    
    def arrayToken(A):
        return str(A)

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        return str(T)

    @staticmethod
    @specialize.memo()
    def sigToken(FUNCTYPE):
        numargs = 0
        for ARG in FUNCTYPE.ARGS:
            if ARG is not lltype.Void:
                numargs += 1
        return numargs     # for now

    @staticmethod
    def erasedType(T):
        if T is llmemory.Address:
            return llmemory.Address
        if isinstance(T, lltype.Primitive):
            return lltype.Signed
        elif isinstance(T, lltype.Ptr):
            return llmemory.GCREF
        else:
            assert 0, "XXX not implemented"


class RGlobalDumpGenOp(RDumpGenOp):
    create_dump = False

global_rgenop = RGlobalDumpGenOp()
RDumpGenOp.constPrebuiltGlobal = global_rgenop.genconst
