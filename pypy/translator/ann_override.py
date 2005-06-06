# overrides for annotation specific to PyPy codebase
from pypy.annotation.policy import AnnotatorPolicy
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import model as annmodel
from pypy.annotation import specialize

class PyPyAnnotatorPolicy(AnnotatorPolicy):

    def override__ignore(pol, *args):
        bk = getbookkeeper()
        return bk.immutablevalue(None)

    def override__instantiate(pol, clspbc):
        assert isinstance(clspbc, annmodel.SomePBC)
        clsdef = None
        for cls, v in clspbc.prebuiltinstances.items():
            if not clsdef:
                clsdef = getbookkeeper().getclassdef(cls)
            else:
                clsdef = clsdef.commonbase(getbookkeeper().getclassdef(cls))
        return annmodel.SomeInstance(clsdef)

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

    specialize__arg1 = staticmethod(specialize.argvalue(1))
    specialize__argtype1 = staticmethod(specialize.argtype(1))
