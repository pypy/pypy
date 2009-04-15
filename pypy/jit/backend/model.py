class AbstractCPU(object):

    def compile_operations(self, loop):
        """Assemble the given list of operations."""
        raise NotImplementedError

    def execute_operations(self, loop, valueboxes):
        """Calls the assembler generated for the given loop.
        Returns the ResOperation that failed, of type rop.FAIL.
        """
        raise NotImplementedError
    
    def get_exception(self):
        raise NotImplementedError

    def get_exc_value(self):
        raise NotImplementedError

    def clear_exception(self):
        raise NotImplementedError

    def set_overflow_error(self):
        raise NotImplementedError

    @staticmethod
    def sizeof(S):
        raise NotImplementedError

    @staticmethod
    def numof(S):
        raise NotImplementedError

    @staticmethod
    def fielddescrof(S, fieldname):
        raise NotImplementedError

    @staticmethod
    def arraydescrof(A):
        raise NotImplementedError

    @staticmethod
    def calldescrof(FUNC, ARGS, RESULT):
        raise NotImplementedError

    @staticmethod
    def methdescrof(METH, methname):
        raise NotImplementedError

    @staticmethod
    def typedescrof(TYPE):
        raise NotImplementedError

    def cast_adr_to_int(self, adr):
        raise NotImplementedError

    def cast_int_to_adr(self, int):
        raise NotImplementedError

    # ---------- the backend-dependent operations ----------

    # lltype specific operations
    # --------------------------
    
    def do_arraylen_gc(self, args, arraydescr):
        raise NotImplementedError

    def do_strlen(self, args, descr=None):
        raise NotImplementedError

    def do_strgetitem(self, args, descr=None):
        raise NotImplementedError

    def do_unicodelen(self, args, descr=None):
        raise NotImplementedError

    def do_unicodegetitem(self, args, descr=None):
        raise NotImplementedError

    def do_getarrayitem_gc(self, args, arraydescr):
        raise NotImplementedError
    
    def do_getfield_gc(self, args, fielddescr):
        raise NotImplementedError
    
    def do_getfield_raw(self, args, fielddescr):
        raise NotImplementedError

    def do_new(self, args, size):
        raise NotImplementedError

    def do_new_with_vtable(self, args, size):
        raise NotImplementedError
    
    def do_new_array(self, args, size):
        raise NotImplementedError
    
    def do_setarrayitem_gc(self, args, arraydescr):
        raise NotImplementedError

    def do_setfield_gc(self, args, fielddescr):
        raise NotImplementedError

    def do_setfield_raw(self, args, fielddescr):
        raise NotImplementedError
        
    def do_newstr(self, args, descr=None):
        raise NotImplementedError

    def do_newunicode(self, args, descr=None):
        raise NotImplementedError

    def do_strsetitem(self, args, descr=None):
        raise NotImplementedError

    def do_unicodesetitem(self, args, descr=None):
        raise NotImplementedError

    def do_call(self, args, calldescr):
        raise NotImplementedError

    def do_cast_int_to_ptr(self, args, descr=None):
        raise NotImplementedError

    def do_cast_ptr_to_int(self, args, descr=None):
        raise NotImplementedError

    # ootype specific operations
    # --------------------------

    def do_oosend(cpu, args, descr=None):
        raise NotImplementedError

    def do_oostring_char(cpu, args, descr=None):
        raise NotImplementedError

    def do_oounicode_unichar(cpu, args, descr=None):
        raise NotImplementedError
