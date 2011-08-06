from pypy.rlib import rstacklet
from pypy.rlib.debug import ll_assert
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.annlowlevel import llhelper


_asmstackrootwalker = None    # BIG HACK: monkey-patched by asmgcroot.py
_stackletrootwalker = None

def get_stackletrootwalker():
    # lazily called, to make the following imports lazy
    global _stackletrootwalker
    if _stackletrootwalker is not None:
        return _stackletrootwalker

    from pypy.rpython.memory.gctransform.asmgcroot import (
        WALKFRAME, CALLEE_SAVED_REGS, sizeofaddr)

    assert _asmstackrootwalker is not None, "should have been monkey-patched"
    basewalker = _asmstackrootwalker

    class StackletRootWalker(object):
        _alloc_flavor_ = "raw"

        enumerating = False

        def setup(self, obj):
            # initialization: read the SUSPSTACK object
            p = llmemory.cast_adr_to_ptr(obj, lltype.Ptr(SUSPSTACK))
            if not p.handle:
                return False
            self.context = p.handle
            anchor = p.anchor
            del p
            self.curframe = lltype.malloc(WALKFRAME, flavor='raw')
            self.otherframe = lltype.malloc(WALKFRAME, flavor='raw')
            initialframedata = anchor[1]
            ll_assert(initialframedata != llmemory.cast_ptr_to_adr(anchor),
                      "no anchored stacklet stack found")
            ll_assert(initialframedata == anchor[0],
                      "more than one anchored stacklet stack found")
            self.fill_initial_frame(self.curframe, initialframedata)
            return True

        def fill_initial_frame(self, curframe, initialframedata):
            # Copy&paste :-(
            initialframedata += 2*sizeofaddr
            reg = 0
            while reg < CALLEE_SAVED_REGS:
                curframe.regs_stored_at[reg] = initialframedata+reg*sizeofaddr
                reg += 1
            retaddraddr = initialframedata + CALLEE_SAVED_REGS * sizeofaddr
            retaddraddr = self.translateptr(retaddraddr)
            curframe.frame_address = retaddraddr.address[0]

        def teardown(self):
            lltype.free(self.curframe, flavor='raw')
            lltype.free(self.otherframe, flavor='raw')
            self.context = lltype.nullptr(rstacklet.handle.TO)
            return llmemory.NULL

        def next(self, obj, prev):
            #
            # Pointers to the stack can be "translated" or not:
            #
            #   * Non-translated pointers point to where the data would be
            #     if the stack was installed and running.
            #
            #   * Translated pointers correspond to where the data
            #     is now really in memory.
            #
            # Note that 'curframe' contains non-translated pointers, and
            # of course the stack itself is full of non-translated pointers.
            #
            while True:
                if not self.enumerating:
                    if not prev:
                        if not self.setup(obj):      # one-time initialization
                            return llmemory.NULL
                        prev = obj   # random value, but non-NULL
                    callee = self.curframe
                    retaddraddr = self.translateptr(callee.frame_address)
                    retaddr = retaddraddr.address[0]
                    basewalker.locate_caller_based_on_retaddr(retaddr)
                    self.enumerating = True
                #
                # not really a loop, but kept this way for similarity
                # with asmgcroot:
                callee = self.curframe
                while True:
                    location = basewalker._shape_decompressor.next()
                    if location == 0:
                        break
                    addr = basewalker.getlocation(callee, location)
                    # yield the translated addr of the next GCREF in the stack
                    return self.translateptr(addr)
                #
                self.enumerating = False
                caller = self.otherframe
                reg = CALLEE_SAVED_REGS - 1
                while reg >= 0:
                    location = basewalker._shape_decompressor.next()
                    addr = basewalker.getlocation(callee, location)
                    caller.regs_stored_at[reg] = addr   # non-translated
                    reg -= 1

                location = basewalker._shape_decompressor.next()
                caller.frame_address = basewalker.getlocation(callee, location)
                # ^^^ non-translated
                if caller.frame_address == llmemory.NULL:
                    return self.teardown()    # completely done with this stack
                #
                self.otherframe = callee
                self.curframe = caller
                # loop back

        def translateptr(self, addr):
            return rstacklet._translate_pointer(self.context, addr)

    _stackletrootwalker = StackletRootWalker()
    return _stackletrootwalker
get_stackletrootwalker._annspecialcase_ = 'specialize:memo'


def customtrace(obj, prev):
    stackletrootwalker = get_stackletrootwalker()
    return stackletrootwalker.next(obj, prev)


ASM_FRAMEDATA_HEAD_PTR = lltype.Ptr(lltype.FixedSizeArray(llmemory.Address, 2))
SUSPSTACK = lltype.GcStruct('SuspStack',
                            ('handle', rstacklet.handle),
                            ('anchor', ASM_FRAMEDATA_HEAD_PTR),
                            ('my_index', lltype.Signed),
                            ('next_unused', lltype.Signed),
                            rtti=True)
CUSTOMTRACEFUNC = lltype.FuncType([llmemory.Address, llmemory.Address],
                                  llmemory.Address)
customtraceptr = llhelper(lltype.Ptr(CUSTOMTRACEFUNC), customtrace)
lltype.attachRuntimeTypeInfo(SUSPSTACK, customtraceptr=customtraceptr)
NULL_SUSPSTACK = lltype.Ptr(SUSPSTACK)


class SuspendedStacks:

    def __init__(self):
        self.lst = []
        self.first_unused = -1
        self.current_index = -1

    def acquire(self):
        if self.first_unused == -1:
            p = lltype.malloc(SUSPSTACK)
            p.handle = lltype.nullptr(rstacklet.handle.TO)
            p.my_index = len(self.lst)
            p.next_unused = -42000000
            p.anchor = lltype.malloc(ASM_FRAMEDATA_HEAD_PTR.TO, flavor='raw',
                                     track_allocation=False)
            self.lst.append(p)
        else:
            p = self.lst[self.first_unused]
            self.first_unused = p.next_unused
        p.anchor[0] = p.anchor[1] = llmemory.cast_ptr_to_adr(p.anchor)
        self.current_index = p.my_index
        return p

    def release(self, p):
        p.next_unused = self.first_unused
        self.first_unused = p.my_index

suspendedstacks = SuspendedStacks()

FUNCNOARG_P = lltype.Ptr(lltype.FuncType([], rstacklet.handle))

pypy_asm_stackwalk2 = rffi.llexternal('pypy_asm_stackwalk',
                                      [FUNCNOARG_P,
                                       ASM_FRAMEDATA_HEAD_PTR],
                                      rstacklet.handle, sandboxsafe=True,
                                      _nowrapper=True)

class StackletGcRootFinder:

    @staticmethod
    def stack_protected_call(callback):
        p = suspendedstacks.acquire()
        llop.gc_assume_young_pointers(lltype.Void,
                                      llmemory.cast_ptr_to_adr(p))
        r = pypy_asm_stackwalk2(callback, p.anchor)
        p.handle = lltype.nullptr(rstacklet.handle.TO)
        suspendedstacks.release(p)
        return r

    @staticmethod
    def set_handle_on_most_recent(h):
        index = suspendedstacks.current_index
        if index >= 0:
            suspendedstacks.lst[index].handle = h
            suspendedstacks.current_index = -1
