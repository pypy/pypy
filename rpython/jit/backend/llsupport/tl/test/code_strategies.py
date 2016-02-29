from hypothesis import strategies as st
from hypothesis.strategies import defines_strategy, composite
from rpython.jit.backend.llsupport.tl import code, interp, stack
from rpython.jit.backend.llsupport.tl.code import (all_types,
        INT_TYP, STR_TYP, LIST_TYP, SHORT_TYP, BYTE_TYP,
        COND_TYP)
from hypothesis.searchstrategy.strategies import OneOfStrategy
from hypothesis.searchstrategy.collections import TupleStrategy

def get_strategy_for(typ):
    if typ == INT_TYP:
        return st.integers(min_value=-2**31, max_value=2**31-1)
    elif typ == SHORT_TYP:
        return st.integers(min_value=-2**15, max_value=2**15-1)
    elif typ == BYTE_TYP:
        return st.integers(min_value=-2**7, max_value=2**7-1)
    elif typ == COND_TYP:
        return st.integers(min_value=0, max_value=4)
    elif typ == STR_TYP:
        return st.text()
    elif typ == LIST_TYP:
        return st.lists(elements=st.one_of(st.integers())) # TODO must be recursive
    else:
        raise NotImplementedError("type: " + str(typ))

@defines_strategy
def wrapped_tl_objects(self, types=all_types):
    if len(types) == 1:
        return get_strategy_for(types[0])
    return OneOfStrategy([get_strategy_for(t) for t in types])

STD_SPACE = interp.Space()

@composite
def runtime_stack(draw, clazz):
    strats = [get_strategy_for(t) for t in clazz._stack_types]
    st = stack.Stack(len(strats))
    for strat in strats:
        st.append(STD_SPACE.wrap(draw(strat)))
    return st

def byte_code_classes():
    for name, clazz in code.__dict__.items():
        if hasattr(clazz, 'BYTE_CODE'):
            yield clazz

@composite
def single_bytecode(draw, clazzes=st.sampled_from(byte_code_classes()),
                    integrals=st.integers(),
                    texts=st.text()):
    clazz = draw(clazzes)
    inst = clazz.create_from(draw, get_strategy_for)
    bytecode, consts = code.Context().transform([inst])
    _stack = draw(runtime_stack(clazz))
    return clazz, bytecode, consts, _stack

