'''Toy Language'''

import py
from bytecode import *

def interp(code=''):
    if not isinstance(code,str):
        raise TypeError("code '%s' should be a string" % str(code))

    code_len = len(code)
    stack = []
    pc = 0

    while pc < code_len:
        opcode = code[pc]
        pc += 1

        if opcode == PUSH:
            stack.append(ord(code[pc]))
            pc += 1

        elif opcode == POP:
            stack.pop()

        elif opcode == ADD:
            stack.append( stack.pop() + stack.pop() )

        else:
            raise RuntimeError("unknown opcode: " + str(opcode))

    return stack[-1]
    
