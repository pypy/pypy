# overrides for annotation specific to PyPy codebase
from pypy.annotation.policy import AnnotatorPolicy
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import specialize

class PyPyAnnotatorPolicy(AnnotatorPolicy):

    def override__wrap_exception_cls(pol, space, x):
        import pypy.objspace.std.typeobject as typeobject
        clsdef = getbookkeeper().getclassdef(typeobject.W_TypeObject)
        return annmodel.SomeInstance(clsdef, can_be_None=True)

    def override__fake_object(pol, space, x):
        from pypy.interpreter import typedef
        clsdef = getbookkeeper().getclassdef(typedef.W_Root)
        return annmodel.SomeInstance(clsdef)    

    def override__cpy_compile(pol, self, source, filename, mode, flags):
        from pypy.interpreter import pycode
        clsdef = getbookkeeper().getclassdef(pycode.PyCode)
        return annmodel.SomeInstance(clsdef)    
