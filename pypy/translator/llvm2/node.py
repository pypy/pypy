class LLVMNode(object):

    def ref(): 
        def _get_ref(self):
            return self._ref 
        def _set_ref(self, ref):
            if hasattr(self, "_ref"):
                raise TypeError, ("can only set ref once! currently: %s" %
                                   (self._ref,))
            if " " in ref: 
                ref = '"%s"' % (ref,)
            self._ref = ref
        return property(_get_ref, _set_ref)
    ref = ref()

    def constructor_ref(): 
        def _get_ref(self):
            return self._constructor_ref 
        def _set_ref(self, ref):
            if hasattr(self, "_constructor_ref"):
                raise TypeError, ("can only set constructor_ref once!"
                                  " currently: %s" % (self._constructor_ref,))
            if " " in ref: 
                ref = '"%s"' % (ref,)
            self._constructor_ref = ref
        return property(_get_ref, _set_ref)
    constructor_ref = constructor_ref()

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
