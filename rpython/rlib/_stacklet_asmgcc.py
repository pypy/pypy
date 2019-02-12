from rpython.rlib.debug import ll_assert
from rpython.rlib import rgc
from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.annlowlevel import llhelper, MixLevelHelperAnnotator
from rpython.annotator import model as annmodel
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.rlib import _rffi_stacklet as _c


_asmstackrootwalker = None    # BIG HACK: monkey-patched by asmgcroot.py
_stackletrootwalker = None

def get_stackletrootwalker():
    # XXX this is too complicated now; we don't need a StackletRootWalker
    # instance to store global state.  We could rewrite it all in one big
    # function.  We don't care enough for now.

    # lazily called, to make the following imports lazy
    global _stackletrootwalker
    if _stackletrootwalker is not None:
        return _stackletrootwalker

    from rpython.memory.gctransform.asmgcroot import (
        WALKFRAME, CALLEE_SAVED_REGS, INDEX_OF_EBP, sizeofaddr)

    assert _asmstackrootwalker is not None, "should have been monkey-patched"
    basewalker = _asmstackrootwalker

    class StackletRootWalker(object):
        _alloc_flavor_ = "raw"

        def setup(self, obj):
            # initialization: read the SUSPSTACK object
            p = llmemory.cast_adr_to_ptr(obj, lltype.Ptr(SUSPSTACK))
            if not p.handle:
                return False
            self.context = llmemory.cast_ptr_to_adr(p.handle)
            self.next_callback_piece = p.callback_pieces
            anchor = p.anchor
            del p
            self.curframe = lltype.malloc(WALKFRAME, flavor='raw')
            self.otherframe = lltype.malloc(WALKFRAME, flavor='raw')
            self.fill_initial_frame(self.curframe, anchor)
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

        def fetch_next_stack_piece(self):
            if self.next_callback_piece == llmemory.NULL:
                lltype.free(self.curframe, flavor='raw')
                lltype.free(self.otherframe, flavor='raw')
                self.context = llmemory.NULL
                return False
            else:
                anchor = self.next_callback_piece
                nextaddr = anchor + sizeofaddr
                nextaddr = self.translateptr(nextaddr)
                self.next_callback_piece = nextaddr.address[0]
                self.fill_initial_frame(self.curframe, anchor)
                return True

        @specialize.arg(3)
        def customtrace(self, gc, obj, callback, arg):
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
            if not self.setup(obj):
                return

            while True:
                callee = self.curframe
                retaddraddr = self.translateptr(callee.frame_address)
                retaddr = retaddraddr.address[0]
                ebp_in_caller = callee.regs_stored_at[INDEX_OF_EBP]
                ebp_in_caller = self.translateptr(ebp_in_caller)
                ebp_in_caller = ebp_in_caller.address[0]
                basewalker.locate_caller_based_on_retaddr(retaddr,
                                                          ebp_in_caller)

                # see asmgcroot for similarity:
                while True:
                    location = basewalker._shape_decompressor.next()
                    if location == 0:
                        break
                    addr = basewalker.getlocation(callee, ebp_in_caller,
                                                  location)
                    # yield the translated addr of the next GCREF in the stack
                    addr = self.translateptr(addr)
                    gc._trace_callback(callback, arg, addr)

                caller = self.otherframe
                reg = CALLEE_SAVED_REGS - 1
                while reg >= 0:
                    location = basewalker._shape_decompressor.next()
                    addr = basewalker.getlocation(callee, ebp_in_caller,
                                                  location)
                    caller.regs_stored_at[reg] = addr   # non-translated
                    reg -= 1

                location = basewalker._shape_decompressor.next()
                caller.frame_address = basewalker.getlocation(callee,
                                                              ebp_in_caller,
                                                              location)
                # ^^^ non-translated
                if caller.frame_address == llmemory.NULL:
                    # completely done with this piece of stack
                    if not self.fetch_next_stack_piece():
                        return
                    continue
                #
                self.otherframe = callee
                self.curframe = caller
                # loop back

        def translateptr(self, addr):
            return _c._translate_pointer(self.context, addr)

    _stackletrootwalker = StackletRootWalker()
    return _stackletrootwalker
get_stackletrootwalker._annspecialcase_ = 'specialize:memo'

def complete_destrptr(gctransformer):
    translator = gctransformer.translator
    mixlevelannotator = MixLevelHelperAnnotator(translator.rtyper)
    args_s = [lltype_to_annotation(lltype.Ptr(SUSPSTACK))]
    s_result = annmodel.s_None
    destrptr = mixlevelannotator.delayedfunction(suspstack_destructor,
                                                 args_s, s_result)
    mixlevelannotator.finish()
    lltype.attachRuntimeTypeInfo(SUSPSTACK, destrptr=destrptr)


def customtrace(gc, obj, callback, arg):
    stackletrootwalker = get_stackletrootwalker()
    stackletrootwalker.customtrace(gc, obj, callback, arg)
lambda_customtrace = lambda: customtrace

def suspstack_destructor(suspstack):
    h = suspstack.handle
    if h:
        _c.destroy(h)


SUSPSTACK = lltype.GcStruct('SuspStack',
                            ('handle', _c.handle),
                            ('anchor', llmemory.Address),
                            ('callback_pieces', llmemory.Address),
                            rtti=True)
NULL_SUSPSTACK = lltype.nullptr(SUSPSTACK)

ASM_FRAMEDATA_HEAD_PTR = lltype.Ptr(lltype.ForwardReference())
ASM_FRAMEDATA_HEAD_PTR.TO.become(lltype.Struct('ASM_FRAMEDATA_HEAD',
        ('prev', ASM_FRAMEDATA_HEAD_PTR),
        ('next', ASM_FRAMEDATA_HEAD_PTR)
    ))
alternateanchor = lltype.malloc(ASM_FRAMEDATA_HEAD_PTR.TO,
                                immortal=True)
alternateanchor.prev = alternateanchor
alternateanchor.next = alternateanchor

FUNCNOARG_P = lltype.Ptr(lltype.FuncType([], _c.handle))
pypy_asm_stackwalk2 = rffi.llexternal('pypy_asm_stackwalk',
                                      [FUNCNOARG_P,
                                       ASM_FRAMEDATA_HEAD_PTR],
                                      lltype.Signed, sandboxsafe=True,
                                      _nowrapper=True)


def _new_callback():
    # Here, we just closed the stack.  Get the stack anchor, store
    # it in the gcrootfinder.suspstack.anchor, and create a new
    # stacklet with stacklet_new().  If this call fails, then we
    # are just returning NULL.
    _stack_just_closed()
    #
    return _c.new(gcrootfinder.newthrd, llhelper(_c.run_fn, _new_runfn),
                  llmemory.NULL)

def _stack_just_closed():
    # Immediately unlink the new stackanchor from the doubly-linked
    # chained list.  When returning from pypy_asm_stackwalk2, the
    # assembler code will try to unlink it again, which should be
    # a no-op given that the doubly-linked list is empty.
    stackanchor = llmemory.cast_ptr_to_adr(alternateanchor.next)
    gcrootfinder.suspstack.anchor = stackanchor
    alternateanchor.prev = alternateanchor
    alternateanchor.next = alternateanchor

def _new_runfn(h, _):
    # Here, we are in a fresh new stacklet.
    llop.gc_stack_bottom(lltype.Void)   # marker for trackgcroot.py
    #
    # There is a fresh suspstack object waiting on the gcrootfinder,
    # so populate it with data that represents the parent suspended
    # stacklet and detach the suspstack object from gcrootfinder.
    suspstack = gcrootfinder.attach_handle_on_suspstack(h)
    #
    # Call the main function provided by the (RPython) user.
    suspstack = gcrootfinder.runfn(suspstack, gcrootfinder.arg)
    #
    # Here, suspstack points to the target stacklet to which we want
    # to jump to next.  Read the 'handle' and forget about the
    # suspstack object.
    return _consume_suspstack(suspstack)

def _consume_suspstack(suspstack):
    h = suspstack.handle
    ll_assert(bool(h), "_consume_suspstack: null handle")
    suspstack.handle = _c.null_handle
    return h

def _switch_callback():
    # Here, we just closed the stack.  Get the stack anchor, store
    # it in the gcrootfinder.suspstack.anchor, and switch to this
    # suspstack with stacklet_switch().  If this call fails, then we
    # are just returning NULL.
    oldanchor = gcrootfinder.suspstack.anchor
    _stack_just_closed()
    h = _consume_suspstack(gcrootfinder.suspstack)
    #
    # gcrootfinder.suspstack.anchor is left with the anchor of the
    # previous place (i.e. before the call to switch()).
    h2 = _c.switch(h)
    #
    if not h2:    # MemoryError: restore
        gcrootfinder.suspstack.anchor = oldanchor
        gcrootfinder.suspstack.handle = h
    return h2


class StackletGcRootFinder(object):
    suspstack = NULL_SUSPSTACK

    def new(self, thrd, callback, arg):
        self.newthrd = thrd._thrd
        self.runfn = callback
        self.arg = arg
        # make a fresh new clean SUSPSTACK
        rgc.register_custom_trace_hook(SUSPSTACK, lambda_customtrace)
        newsuspstack = lltype.malloc(SUSPSTACK)
        newsuspstack.handle = _c.null_handle
        self.suspstack = newsuspstack
        # Invoke '_new_callback' by closing the stack
        #
        callback_pieces = llop.gc_detach_callback_pieces(llmemory.Address)
        newsuspstack.callback_pieces = callback_pieces
        #
        h = pypy_asm_stackwalk2(llhelper(FUNCNOARG_P, _new_callback),
                                alternateanchor)
        h = rffi.cast(_c.handle, h)
        #
        llop.gc_reattach_callback_pieces(lltype.Void, callback_pieces)
        return self.get_result_suspstack(h)

    def switch(self, suspstack):
        # Immediately before the switch, 'suspstack' describes the suspended
        # state of the *target* of the switch.  Then it is theoretically
        # freed.  In fact what occurs is that we reuse the same 'suspstack'
        # object in the target, just after the switch, to store the
        # description of where we came from.  Then that "other" 'suspstack'
        # object is returned.
        self.suspstack = suspstack
        #
        callback_pieces = llop.gc_detach_callback_pieces(llmemory.Address)
        old_callback_pieces = suspstack.callback_pieces
        suspstack.callback_pieces = callback_pieces
        #
        h = pypy_asm_stackwalk2(llhelper(FUNCNOARG_P, _switch_callback),
                                alternateanchor)
        h = rffi.cast(_c.handle, h)
        #
        llop.gc_reattach_callback_pieces(lltype.Void, callback_pieces)
        if not h:
            self.suspstack.callback_pieces = old_callback_pieces
        #
        return self.get_result_suspstack(h)

    def attach_handle_on_suspstack(self, handle):
        s = self.suspstack
        self.suspstack = NULL_SUSPSTACK
        ll_assert(bool(s.anchor), "s.anchor should not be null")
        s.handle = handle
        llop.gc_writebarrier(lltype.Void, llmemory.cast_ptr_to_adr(s))
        return s

    def get_result_suspstack(self, h):
        #
        # Return from a new() or a switch(): 'h' is a handle, possibly
        # an empty one, that says from where we switched to.
        if not h:
            raise MemoryError
        elif _c.is_empty_handle(h):
            return NULL_SUSPSTACK
        else:
            # This is a return that gave us a real handle.  Store it.
            return self.attach_handle_on_suspstack(h)

    def is_empty_handle(self, suspstack):
        return not suspstack

    def get_null_handle(self):
        return NULL_SUSPSTACK


gcrootfinder = StackletGcRootFinder()
