class LLVMNode(object):
    def _get_ref(self):
        return self._ref
    def _set_ref(self, ref):
        if hasattr(self, "_ref"):
            raise TypeError, ("can only set ref once! currently: %s" %
                               (self._ref,))
        self._ref = ref
    ref = property(_get_ref, _set_ref)

    # __________________ before "implementation" ____________________
    def writedatatypedecl(self, codewriter):
        """ write out declare names of data types 
            (structs/arrays/function pointers)
        """

    def writeglobalconstants(self, codewriter):
        """ write out global values.  """

    def writedecl(self, codewriter):
        """ write function forward declarations. """ 

    # __________________ after "implementation" ____________________
    def writeimpl(self, codewriter):
        """ write function implementations. """ 
