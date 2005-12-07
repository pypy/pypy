'''Toy Language'''

import py
from bytecode import *

def char2int(c):
    t = ord(c)
    if t & 128:
        t = -(-ord(c) & 0xff)
    return t

def interp(code=''):
    if not isinstance(code,str):
        raise TypeError("code '%s' should be a string" % str(code))

    code_len = len(code)
    stack = []
    pc = 0

    while pc < code_len:
        opcode = ord(code[pc])
        pc += 1

        if opcode == PUSH:
            stack.append( char2int(code[pc]) )
            pc += 1

        elif opcode == POP:
            stack.pop()

        elif opcode == SWAP:
            a, b = stack.pop(), stack.pop()
            stack.append(a)
            stack.append(b)

        elif opcode == ROT: #rotate stack top to somewhere below
            r = char2int(code[pc])
            if r > 1:
                i = len(stack) - r
                if i < 0:
                    raise IndexError
                stack.insert( i, stack.pop() )
            pc += 1

        elif opcode == PICK:
            stack.append( stack[-1 - char2int(code[pc])] )
            pc += 1

        elif opcode == PUT:
            stack[-1 - char2int(code[pc])] = stack.pop()
            pc += 1

        elif opcode == ADD:
            a, b = stack.pop(), stack.pop()
            stack.append( b + a )

        elif opcode == SUB:
            a, b = stack.pop(), stack.pop()
            stack.append( b - a )

        elif opcode == MUL:
            a, b = stack.pop(), stack.pop()
            stack.append( b * a )

        elif opcode == DIV:
            a, b = stack.pop(), stack.pop()
            stack.append( b / a )

        elif opcode == EQ:
            a, b = stack.pop(), stack.pop()
            stack.append( b == a )

        elif opcode == NE:
            a, b = stack.pop(), stack.pop()
            stack.append( b != a )

        elif opcode == LT:
            a, b = stack.pop(), stack.pop()
            stack.append( b <  a )

        elif opcode == LE:
            a, b = stack.pop(), stack.pop()
            stack.append( b <= a )

        elif opcode == GT:
            a, b = stack.pop(), stack.pop()
            stack.append( b >  a )

        elif opcode == GE:
            a, b = stack.pop(), stack.pop()
            stack.append( b >= a )

        elif opcode == BR_COND:
            if stack.pop():
                pc += char2int(code[pc])
            pc += 1

        elif opcode == CALL:
            stack.append( pc+1 )
            pc += char2int(code[pc]) + 1

        elif opcode == RETURN:
            pc = stack.pop()

        elif opcode == EXIT:
            break

        else:
            raise RuntimeError("unknown opcode: " + str(opcode))

    return stack[-1]
