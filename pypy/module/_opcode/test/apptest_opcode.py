import pytest

import opcode

def test_errors():
    pytest.raises(ValueError, opcode.stack_effect, opcode.opmap["LOAD_CONST"])
    pytest.raises(ValueError, opcode.stack_effect, opcode.opmap["BINARY_ADD"], 1)
    pytest.raises(ValueError, opcode.stack_effect, 1231231)

def test_call_function():
    assert opcode.stack_effect(opcode.opmap["CALL_FUNCTION"], 3) == -3
    assert opcode.stack_effect(opcode.opmap["EXTENDED_ARG"], 3) == 0

def test_invalid_opcode():
    pytest.raises(ValueError, opcode.stack_effect, 0)
    pytest.raises(ValueError, opcode.stack_effect, 0, 0)
