from rpython.rlib.clibffi import FFI_DEFAULT_ABI

class AbstractCallBuilder(object):

    # this is the calling convention (can be FFI_STDCALL on Windows)
    callconv = FFI_DEFAULT_ABI

    # is it for the main CALL of a call_release_gil?
    is_call_release_gil = False

    # set by save_result_value()
    tmpresloc = None

    def __init__(self, assembler, fnloc, arglocs, resloc, restype, ressize):
        # Avoid tons of issues with a non-immediate fnloc by sticking it
        # as an extra argument if needed
        self.fnloc = fnloc
        self.arglocs = arglocs
        self.asm = assembler
        self.mc = assembler.mc
        self.resloc = resloc
        self.restype = restype
        self.ressize = ressize
        self.ressigned = False

    def emit_no_collect(self):
        """Emit a call that cannot collect."""
        self.prepare_arguments()
        self.emit_raw_call()
        self.restore_stack_pointer()
        self.load_result()

    def emit(self):
        """Emit a regular call; not for CALL_RELEASE_GIL."""
        self.prepare_arguments()
        self.push_gcmap()
        self.emit_raw_call()
        self.restore_stack_pointer()
        self.pop_gcmap()
        self.load_result()

    def emit_call_release_gil(self):
        """Emit a CALL_RELEASE_GIL, including calls to releasegil_addr
        and reacqgil_addr."""
        self.select_call_release_gil_mode()
        self.prepare_arguments()
        self.push_gcmap_for_call_release_gil()
        self.call_releasegil_addr_and_move_real_arguments()
        self.emit_raw_call()
        self.restore_stack_pointer()
        self.move_real_result_and_call_reacqgil_addr()
        self.pop_gcmap()
        self.load_result()

    def select_call_release_gil_mode(self):
        """Overridden in CallBuilder64"""
        self.is_call_release_gil = True

    def prepare_arguments(self):
        raise NotImplementedError

    def push_gcmap(self):
        raise NotImplementedError

    def pop_gcmap(self):
        raise NotImplementedError

    def emit_raw_call(self):
        raise NotImplementedError

    def restore_stack_pointer(self):
        raise NotImplementedError

    def load_result(self):
        raise NotImplementedError
