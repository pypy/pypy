class PrologError(Exception):
    pass

class CatchableError(PrologError):
    def __init__(self, errorterm):
        from pypy.lang.prolog.interpreter import term
        self.term = term.Term("error", [errorterm])

class UserError(CatchableError):
    def __init__(self, errorterm):
        self.term = errorterm

class UncatchableError(PrologError):
    def __init__(self, message):
        self.message = message

class UnificationFailed(PrologError):
    pass

class FunctionNotFound(PrologError):
    def __init__(self, signature):
        self.signature = signature

class CutException(PrologError):
    def __init__(self, continuation):
        self.continuation = continuation

def throw_instantiation_error():
    from pypy.lang.prolog.interpreter import term
    raise CatchableError(term.Atom.newatom("instantiation_error"))

def throw_type_error(valid_type, obj):
    from pypy.lang.prolog.interpreter import term
    # valid types are:
    # atom, atomic, byte, callable, character
    # evaluable, in_byte, in_character, integer, list
    # number, predicate_indicator, variable
    from pypy.lang.prolog.interpreter import term
    raise CatchableError(
        term.Term("type_error", [term.Atom.newatom(valid_type), obj]))

def throw_domain_error(valid_domain, obj):
    from pypy.lang.prolog.interpreter import term
    # valid domains are:
    # character_code_list, close_option, flag_value, io_mode,
    # not_empty_list, not_less_than_zero, operator_priority,
    # operator_specifier, prolog_flag, read_option, source_sink,
    # stream, stream_option, stream_or_alias, stream_position,
    # stream_property, write_option
    raise CatchableError(
        term.Term("domain_error", [term.Atom.newatom(valid_domain), obj]))

def throw_existence_error(object_type, obj):
    from pypy.lang.prolog.interpreter import term
    # valid types are:
    # procedure, source_sink, stream
    raise CatchableError(
        term.Term("existence_error", [term.Atom.newatom(object_type), obj]))

def throw_permission_error(operation, permission_type, obj):
    from pypy.lang.prolog.interpreter import term
    # valid operations are:
    # access, create, input, modify, open, output, reposition 

    # valid permission_types are:
    # binary_stream, flag, operator, past_end_of_stream, private_procedure,
    # static_procedure, source_sink, stream, text_stream. 
    raise CatchableError(
        term.Term("permission_error", [term.Atom.newatom(operation),
                                       term.Atom.newatom(permission_type),
                                       obj]))
