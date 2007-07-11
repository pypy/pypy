from pypy.translator.translator import graphof

# ___________________________________________________________________________

def throwZeroDivisionError():
    raise ZeroDivisionError

def throwIndexError():
    raise IndexError

def throwOverflowError():
    raise OverflowError

# ___________________________________________________________________________

def create_interlink_node(db):
    """ Translates the create_interlink_impl() function and returns
    a jvmgen.Method object that allows it to be called. """
    translator = db.genoo.translator

    HELPERS = [val for nm, val in globals().items() if nm.startswith('throw')]
    
    for func in HELPERS:
        translator.annotator.build_types(func, [])        
    translator.rtyper.specialize_more_blocks()

    helpers = {}
    for func in HELPERS:
        graph = graphof(translator, func)
        helpers[func.func_name] = db.pending_function(graph)

    db.create_interlink_node(helpers)

