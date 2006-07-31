from pypy.translator.cli.function import Function

class Helper(Function):
    def render(self, ilasm):
        ilasm.begin_namespace('pypy.runtime')
        ilasm.begin_class('Helpers')
        Function.render(self, ilasm)
        ilasm.end_class()
        ilasm.end_namespace()

def get_prebuilt_nodes(translator, db):
    raise_OSError_graph = translator.rtyper.exceptiondata.fn_raise_OSError.graph
    return [Helper(db, raise_OSError_graph, 'raise_OSError')]
