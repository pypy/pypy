"""
This backend records all operations that the JIT front-end tries to do,
and writes them as pseudo-Python source in

    /tmp/usession-<yourname>/rdumpgenop.py.
"""
import os
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.codegen.model import GenBuilder, CodeGenSwitch
from pypy.jit.codegen.llgraph import rgenop as llrgenop
from pypy.tool.udir import udir

LOGFILE = str(udir.join('rdumpgenop.py'))


class FlexSwitch(CodeGenSwitch):
    def __init__(self, rgenop, fs):
        self.rgenop = rgenop
        self.fs = fs
        self.name = rgenop.count('flexswitch')
        self.dump = rgenop.dump

    def add_case(self, gv_case):
        b = self.fs.add_case(gv_case)
        b = Builder(self.rgenop, b)
        self.dump("%s = %s.add_case(%s)" % (b.name,
                                            self.name,
                                            self.rgenop.vname(gv_case)))
        return b


class Builder(GenBuilder):

    def __init__(self, rgenop, llbuilder):
        self.rgenop = rgenop
        self.llbuilder = llbuilder
        self.name = rgenop.count('builder')
        self.dump = rgenop.dump

    def start_writing(self):
        self.dump("%s.start_writing()" % self.name)
        self.llbuilder.start_writing()

    def enter_next_block(self, kinds, args_gv):
        self.dump("args_gv = [%s]" % self.rgenop.vlistname(args_gv))
        lbl = self.llbuilder.enter_next_block(kinds, args_gv)
        self.dump("%s = %s.enter_next_block([%s], args_gv)" % (
            self.rgenop.lblname(lbl),
            self.name,
            self.rgenop.kindtokensname(kinds)))
        self.dump("%s = args_gv" % self.rgenop.vlistassname(args_gv))
        return lbl

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        b = self.llbuilder.jump_if_false(gv_condition, args_for_jump_gv)
        b = Builder(self.rgenop, b)
        self.dump("%s = %s.jump_if_false(%s, [%s])" % (
            b.name,
            self.name,
            self.rgenop.vname(gv_condition),
            self.rgenop.vlistname(args_for_jump_gv)))
        return b

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        b = self.llbuilder.jump_if_true(gv_condition, args_for_jump_gv)
        b = Builder(self.rgenop, b)
        self.dump("%s = %s.jump_if_true(%s, [%s])" % (
            b.name,
            self.name,
            self.rgenop.vname(gv_condition),
            self.rgenop.vlistname(args_for_jump_gv)))
        return b

    def finish_and_goto(self, outputargs_gv, targetlbl):
        self.dump("%s.finish_and_goto([%s], %s)" % (
            self.name,
            self.rgenop.vlistname(outputargs_gv),
            self.rgenop.lblname(targetlbl)))
        self.llbuilder.finish_and_goto(outputargs_gv, targetlbl)

    def finish_and_return(self, sigtoken, gv_returnvar):
        self.dump("%s.finish_and_return(%s, %s)" % (
            self.name,
            self.rgenop.sigtokenname(sigtoken),
            self.rgenop.vname(gv_returnvar)))
        self.llbuilder.finish_and_return(sigtoken, gv_returnvar)

    def pause_writing(self, alive_gv):
        b = self.llbuilder.pause_writing(alive_gv)
        b = Builder(self.rgenop, b)
        self.dump("%s = %s.pause_writing([%s])" % (
            b.name,
            self.name,
            self.rgenop.vlistname(alive_gv)))
        return b

    def end(self):
        self.dump("%s.end()" % (self.name,))
        self.llbuilder.end()

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        v = self.llbuilder.genop1(opname, gv_arg)
        self.dump("%s = %s.genop1('%s', %s)" % (
            self.rgenop.vname(v),
            self.name,
            opname,
            self.rgenop.vname(gv_arg)))
        return v

    @specialize.arg(1)
    def genraisingop1(self, opname, gv_arg):
        v1, v2 = self.llbuilder.genraisingop1(opname, gv_arg)
        self.dump("%s, %s = %s.genraisingop1('%s', %s)" % (
            self.rgenop.vname(v1),
            self.rgenop.vname(v2),
            self.name,
            opname,
            self.rgenop.vname(gv_arg)))
        return v1, v2

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        v = self.llbuilder.genop2(opname, gv_arg1, gv_arg2)
        self.dump("%s = %s.genop2('%s', %s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            opname,
            self.rgenop.vname(gv_arg1),
            self.rgenop.vname(gv_arg2)))
        return v

    @specialize.arg(1)
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        v1, v2 = self.llbuilder.genraisingop2(opname, gv_arg1, gv_arg2)
        self.dump("%s, %s = %s.genraisingop2('%s', %s, %s)" % (
            self.rgenop.vname(v1),
            self.rgenop.vname(v2),
            self.name,
            opname,
            self.rgenop.vname(gv_arg1),
            self.rgenop.vname(gv_arg2)))
        return v1, v2

    def genop_ptr_iszero(self, kind, gv_ptr):
        v = self.llbuilder.genop_ptr_iszero(kind, gv_ptr)
        self.dump("%s = %s.genop_ptr_iszero(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            self.rgenop.vname(gv_ptr)))
        return v

    def genop_ptr_nonzero(self, kind, gv_ptr):
        v = self.llbuilder.genop_ptr_nonzero(kind, gv_ptr)
        self.dump("%s = %s.genop_ptr_nonzero(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            self.rgenop.vname(gv_ptr)))
        return v

    def genop_ptr_eq(self, kind, gv_ptr1, gv_ptr2):
        v = self.llbuilder.genop_ptr_eq(kind, gv_ptr1, gv_ptr2)
        self.dump("%s = %s.genop_ptr_eq(%s, %s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            self.rgenop.vname(gv_ptr1),
            self.rgenop.vname(gv_ptr2)))
        return v

    def genop_ptr_ne(self, kind, gv_ptr1, gv_ptr2):
        v = self.llbuilder.genop_ptr_ne(kind, gv_ptr1, gv_ptr2)
        self.dump("%s = %s.genop_ptr_ne(%s, %s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            self.rgenop.vname(gv_ptr1),
            self.rgenop.vname(gv_ptr2)))
        return v

    def genop_same_as(self, kind, gv_x):
        v = self.llbuilder.genop_same_as(kind, gv_x)
        self.dump("%s = %s.genop_same_as(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            self.rgenop.vname(gv_x)))
        return v

    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        v = self.llbuilder.genop_call(sigtoken, gv_fnptr, args_gv)
        self.dump("%s = %s.genop_call(%s, %s, [%s])" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.sigtokenname(sigtoken),
            self.rgenop.vname(gv_fnptr),
            self.rgenop.vlistname(args_gv)))
        return v

    def genop_malloc_fixedsize(self, alloctoken):
        v = self.llbuilder.genop_malloc_fixedsize(alloctoken)
        self.dump("%s = %s.genop_malloc_fixedsize(%s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.alloctokenname(alloctoken)))
        return v

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        v = self.llbuilder.genop_malloc_varsize(varsizealloctoken, gv_size)
        self.dump("%s = %s.genop_malloc_varsize(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.varsizealloctokenname(varsizealloctoken),
            self.rgenop.vname(gv_size)))
        return v

    def genop_getfield(self, fieldtoken, gv_ptr):
        v = self.llbuilder.genop_getfield(fieldtoken, gv_ptr)
        self.dump("%s = %s.genop_getfield(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.fieldtokenname(fieldtoken),
            self.rgenop.vname(gv_ptr)))
        return v

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        self.dump("%s.genop_setfield(%s, %s, %s)" % (
            self.name,
            self.rgenop.fieldtokenname(fieldtoken),
            self.rgenop.vname(gv_ptr),
            self.rgenop.vname(gv_value)))
        self.llbuilder.genop_setfield(fieldtoken, gv_ptr, gv_value)

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        v = self.llbuilder.genop_getsubstruct(fieldtoken, gv_ptr)
        self.dump("%s = %s.genop_getsubstruct(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.fieldtokenname(fieldtoken),
            self.rgenop.vname(gv_ptr)))
        return v

    def genop_getarrayitem(self, arraytoken, gv_array, gv_index):
        v = self.llbuilder.genop_getarrayitem(arraytoken, gv_array, gv_index)
        self.dump("%s = %s.genop_getarrayitem(%s, %s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.arraytokenname(arraytoken),
            self.rgenop.vname(gv_array),
            self.rgenop.vname(gv_index)))
        return v

    def genop_setarrayitem(self, arraytoken, gv_array, gv_index, gv_value):
        self.dump("%s.genop_setarrayitem(%s, %s, %s, %s)" % (
            self.name,
            self.rgenop.arraytokenname(arraytoken),
            self.rgenop.vname(gv_array),
            self.rgenop.vname(gv_index),
            self.rgenop.vname(gv_value)))
        self.llbuilder.genop_setarrayitem(arraytoken, gv_array,
                                          gv_index, gv_value)

    def genop_getarraysubstruct(self, arraytoken, gv_array, gv_index):
        v = self.llbuilder.genop_getarraysubstruct(arraytoken, gv_array,
                                                   gv_index)
        self.dump("%s = %s.genop_getarraysubstruct(%s, %s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.arraytokenname(arraytoken),
            self.rgenop.vname(gv_array),
            self.rgenop.vname(gv_index)))
        return v

    def genop_getarraysize(self, arraytoken, gv_array):
        v = self.llbuilder.genop_getarraysize(arraytoken, gv_array)
        self.dump("%s = %s.genop_getarraysize(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.arraytokenname(arraytoken),
            self.rgenop.vname(gv_array)))
        return v

    def flexswitch(self, gv_exitswitch, args_gv):
        fs, b = self.llbuilder.flexswitch(gv_exitswitch, args_gv)
        fs = FlexSwitch(self.rgenop, fs)
        b = Builder(self.rgenop, b)
        self.dump("%s, %s = %s.flexswitch(%s, [%s])" % (
            fs.name,
            b.name,
            self.name,
            self.rgenop.vname(gv_exitswitch),
            self.rgenop.vlistname(args_gv)))
        return fs, b

    def show_incremental_progress(self):
        self.llbuilder.show_incremental_progress()

    def log(self, msg):
        self.rgenop.dump('# log: %s' % (msg,))

    def genop_get_frame_base(self):
        v = self.llbuilder.genop_get_frame_base()
        self.dump("%s = %s.genop_get_frame_base()" % (
            self.rgenop.vname(v),
            self.name))
        return v

    def get_frame_info(self, vars_gv):
        info = self.llbuilder.get_frame_info(vars_gv)
        self.dump("%s = %s.get_frame_info([%s])" % (
            info,
            self.name,
            self.rgenop.vlistname(vars_gv)))
        return info

    def alloc_frame_place(self, kind, gv_initial_value=None):
        place = self.llbuilder.alloc_frame_place(kind, gv_initial_value)
        if gv_initial_value is None:
            s = 'None'
        else:
            s = self.rgenop.vname(gv_initial_value)
        self.dump("%s = %s.alloc_frame_place(%s, %s)" % (
            place,
            self.name,
            self.rgenop.kindtokenname(kind),
            s))
        return place

    def genop_absorb_place(self, kind, place):
        v = self.llbuilder.genop_absorb_place(kind, place)
        self.dump("%s = %s.genop_absorb_place(%s, %s)" % (
            self.rgenop.vname(v),
            self.name,
            self.rgenop.kindtokenname(kind),
            place))
        return v


class RDumpGenOp(llrgenop.RGenOp):

    def __init__(self):
        self.keepalive_gc_refs = []
        self.counters = {}
        self.vnames = {}
        self.lblnames = {}
        self.dump("# ------------------------------------------------------------")

    def count(self, prefix):
        count = self.counters.get(prefix, 0)
        self.counters[prefix] = count + 1
        return '%s%d' % (prefix, count)

    def vname(self, gv):
        try:
            return self.vnames[gv]
        except KeyError:
            if not gv.is_const:
                name = self.count('v')
            else:
                name = 'rgenop.genconst(%s)' % gv.revealconstrepr()
            self.vnames[gv] = name
            return name

    def vlistname(self, list_gv):
        return ', '.join([self.vname(v) for v in list_gv])

    def vlistassname(self, list_gv):
        # [] = x  => SyntaxError, grumble
        if list_gv:
            return '[%s]' % self.vlistname(list_gv)
        else:
            return '_'

    def lblname(self, lbl):
        try:
            return self.lblnames[lbl]
        except KeyError:
            name = self.count('label')
            self.lblnames[lbl] = name
            return name

    def kindtokenname(self, kindtoken):
        return kindtokennames.get(kindtoken, 'kindtoken')

    def kindtokensname(self, kindtokens):
        return ', '.join([self.kindtokenname(k) for k in kindtokens])

    def sigtokenname(self, sigtoken):
        numargs = len(sigtoken[0])
        return 'rgenop.sigToken(FUNC%d)' % numargs

    def alloctokenname(self, alloctoken):
        return 'alloctoken'

    def varsizealloctokenname(self, varsizealloctoken):
        return 'varsizealloctoken'

    def fieldtokenname(self, fieldtoken):
        return 'fieldtoken'

    def arraytokenname(self, arraytoken):
        return 'arraytoken'

    @staticmethod
    @specialize.memo()
    def kindToken(T):
        result = llrgenop.rgenop.kindToken(T)
        kindtokennames[result] = str(T).lower() + '_kind'
        return result

    @staticmethod
    def dump(text):
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

    def newgraph(self, sigtoken, name):
        builder, gv_callable, inputargs_gv = llrgenop.RGenOp.newgraph(
            self, sigtoken, name)
        builder = Builder(self, builder)
        self.dump("# new graph %s" % self.vname(gv_callable))
        self.dump("%s, gv_callable, %s = rgenop.newgraph(%s, '%s')" % (
            builder.name,
            self.vlistassname(inputargs_gv),
            self.sigtokenname(sigtoken),
            name))
        return builder, gv_callable, inputargs_gv

    def replay(self, label, kinds):
        self.dump("# replay")
        b, args_gv = llrgenop.RGenOp.replay(self, label, kinds)
        b = Builder(self, b)
        self.dump("%s, %s = rgenop.replay(%s, [%s])" % (
            b.name,
            self.vlistassname(args_gv),
            self.lblname(label),
            self.kindtokensname(kinds)))
        return b, args_gv

    @staticmethod
    @specialize.arg(0)
    def read_frame_var(T, base, info, index):
        RDumpGenOp.dump("# read_frame_var(info=%s, index=%d)" % (info, index))
        return llrgenop.RGenOp.read_frame_var(T, base, info, index)

    @staticmethod
    @specialize.arg(0)
    def write_frame_place(T, base, place, value):
        RDumpGenOp.dump("# write_frame_place(place=%s)" % (place,))
        llrgenop.RGenOp.write_frame_place(T, base, place, value)

    @staticmethod
    @specialize.arg(0)
    def read_frame_place(T, base, place):
        RDumpGenOp.dump("# read_frame_place(place=%s)" % (place,))
        return llrgenop.RGenOp.read_frame_place(T, base, place)

kindtokennames = {}
