class LLVMNode(object):
    nodename_count = {}

    def make_name(self, name):
        if name in self.nodename_count:
            postfix = '.%d' % self.nodename_count[name]
            self.nodename_count[name] += 1
        else:
            postfix = ''
            self.nodename_count[name] = 1
        return name + postfix

    def make_ref(self, prefix, name):
        return self.make_name(prefix + name)

    def ref(): 
        def _get_ref(self):
            return self._ref 
        def _set_ref(self, ref):
            if hasattr(self, "_ref"):
                raise TypeError, ("can only set ref once! currently: %s" %
                                   (self._ref,))
            if " " in ref or "<" in ref: 
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

    def setup(self):
        pass

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

class ConstantLLVMNode(LLVMNode):

    def castfrom(self):
        return None
