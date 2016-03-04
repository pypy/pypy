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

@defines_strategy
def stack_entry(types=all_types):
    return st.one_of(*[get_strategy_for(t) for t in types])

@defines_strategy
def runtime_stack(min_size=0, average_size=5, max_size=4096,
          types=all_types):
    if max_size < average_size:
        average_size = max_size // 2
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

def find_next(stack, type, off=0):
    i = off
    while i < stack.size():
        if stack.peek(i).is_of_type(LIST_TYP):
            break
        i += 1
    else:
        return None
    return stack.peek(i)

@defines_strategy
def bytecode_class(stack):
    def filter_using_stack(bytecode_class):
        required_types = bytecode_class._stack_types
        if len(required_types) > stack.size():
            return False
        for i in range(len(required_types)):
            item = stack.peek(i)
            j = len(required_types) - i - 1
            rt = required_types[j]
            if not item.is_of_type(rt):
                return False
        if code.op_modifies_list(bytecode_class):
            w_list = find_next(stack, LIST_TYP)
            if w_list is None or len(w_list.items) == 0:
                # on an empty list we cannot insert or delete
                return False
        return True
    clazzes = filter(filter_using_stack, byte_code_classes())
    return st.sampled_from(clazzes)

@composite
def bytecode(draw, max_stack_size=4096):
    # get a stack that is the same for one test run
    stack_strat = runtime_stack(max_size=max_stack_size)
    run_stack = draw(st.shared(stack_strat, 'stack'))

    # get a byte code class
    clazz = draw(bytecode_class(run_stack))
    inst = clazz.create_from(draw, get_strategy_for)
    assume(not inst.filter_bytecode(run_stack))
    bytecode, consts = code.Context().transform([inst])

    # propagate the changes to the stack
    orig_stack = run_stack.copy()
    interp.dispatch_once(STD_SPACE, 0, bytecode, consts, run_stack)
    return inst, orig_stack
