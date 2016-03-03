from hypothesis import strategies as st
from hypothesis.control import assume
from hypothesis.strategies import defines_strategy, composite
from rpython.jit.backend.llsupport.tl import code, interp, stack
from rpython.jit.backend.llsupport.tl.code import (all_types,
        INT_TYP, STR_TYP, LIST_TYP, SHORT_TYP, BYTE_TYP,
        COND_TYP, IDX_TYP)
from hypothesis.searchstrategy.strategies import OneOfStrategy
from hypothesis.searchstrategy.collections import TupleStrategy

def get_strategy_for(typ):
    if typ == INT_TYP:
        return st.integers(min_value=-2**31, max_value=2**31-1)
    elif typ == IDX_TYP:
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

STD_SPACE = interp.Space()

#@composite
#def runtime_stack(draw, clazz):
#    strats = [get_strategy_for(t) for t in clazz._stack_types]
#    stack_obj = stack.Stack(len(strats))
#    for i,strat in enumerate(strats):
#        if clazz._stack_types[i] == IDX_TYP:
#            # it is only valid to access a list with a valid index!
#            w_list = stack_obj.peek(i-1)
#            l = len(w_list.items)
#            assume(l > 0)
#            integrals = st.integers(min_value=0, max_value=l-1)
#            stack_obj.append(STD_SPACE.wrap(draw(integrals)))
#            continue
#        stack_obj.append(STD_SPACE.wrap(draw(strat)))
#    return stack_obj

@defines_strategy
def stack_entry(types=all_types):
    return st.sampled_from([get_strategy_for(t) for t in types])

@defines_strategy
def runtime_stack(min_size=0, average_size=5, max_size=4096,
          types=all_types):
    stack_entries = st.lists(stack_entry(all_types), min_size,
                             average_size, max_size)
    return stack_entries.map(lambda elems: \
                                stack.Stack.from_items(STD_SPACE, elems))

def byte_code_classes():
    for name, clazz in code.__dict__.items():
        if hasattr(clazz, 'BYTE_CODE'):
            yield clazz

def get_byte_code_class(num):
    for clazz in byte_code_classes():
        if clazz.BYTE_CODE == num:
            return clazz
    return None


@defines_strategy
def bytecode_class(stack):
    def filter_using_stack(bytecode_class):
        required_types = bytecode_class.requires_stack
        if len(required_types) < stack.size():
            return False
        j = len(required_types)-1
        for i in range(stack.size()):
            item = stack.peek(i)
            if not item.is_of_type(required_types[j]):
                return False
            j -= 1
            if j < 0:
                break
        return True
    return st.sampled_from(byte_code_classes()).filter(filter_using_stack)

@composite
def bytecode(draw, max_stack_size=4096):
    # get a stack that is the same for one test run
    rs = runtime_stack(max_size=max_stack_size)
    stack = draw(st.shared(rs, 'stack'))
    clazz = draw(bytecode_class(stack))
    inst = clazz.create_from(draw, get_strategy_for)
    bytecode, consts = code.Context().transform([inst])
    return bytecode, consts, stack
