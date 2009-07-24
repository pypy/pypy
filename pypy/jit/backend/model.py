class AbstractCPU(object):

    def set_class_sizes(self, class_sizes):
        self.class_sizes = class_sizes

    def setup_once(self):
        """Called once by the front-end when the program starts."""
        pass

    def compile_operations(self, loop):
        """Assemble the given list of operations."""
        raise NotImplementedError

    def execute_operations(self, loop):
        """Calls the assembler generated for the given loop.
        Returns the ResOperation that failed, of type rop.FAIL.
        Use set_future_value_xxx() before, and get_latest_value_xxx() after.
        """
        raise NotImplementedError

    def set_future_value_int(self, index, intvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_ptr(self, index, ptrvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def set_future_value_obj(self, index, objvalue):
        """Set the value for the index'th argument for the loop to run."""
        raise NotImplementedError

    def get_latest_value_int(self, index):
        """Returns the value for the index'th argument to the
        lastest rop.FAIL.  Returns an int."""
        raise NotImplementedError

    def get_latest_value_ptr(self, index):
        """Returns the value for the index'th argument to the
        lastest rop.FAIL.  Returns a ptr."""
        raise NotImplementedError

    def get_latest_value_obj(self, index):
        """Returns the value for the index'th argument to the
        lastest rop.FAIL.  Returns an obj."""
        raise NotImplementedError

    def get_exception(self):
        raise NotImplementedError

    def get_exc_value(self):
        raise NotImplementedError

    def clear_exception(self):
        raise NotImplementedError

    def set_overflow_error(self):
        raise NotImplementedError

    def set_zero_division_error(self):
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
    def methdescrof(SELFTYPE, methname):
        # must return a subclass of history.AbstractMethDescr
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

    def do_new(self, args, sizedescr):
        raise NotImplementedError

    def do_new_with_vtable(self, args, sizedescr):
        raise NotImplementedError
    
    def do_new_array(self, args, arraydescr):
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

    def do_runtimenew(self, args, descr=None):
        raise NotImplementedError

    def do_oosend(self, args, descr=None):
        raise NotImplementedError

    def do_instanceof(self, args, descr=None):
        raise NotImplementedError
