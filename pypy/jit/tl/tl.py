'''Toy Language'''

import py
from pypy.jit.tl.opcode import *
from pypy.jit.tl import opcode as tlopcode
from pypy.rpython.objectmodel import hint

def char2int(c):
    t = ord(c)
    if t & 128:
        t = -(-ord(c) & 0xff)
    return t

def make_interp(supports_call):
    def interp(code='', pc=0, inputarg=0):
        if not isinstance(code,str):
            raise TypeError("code '%s' should be a string" % str(code))

        code_len = len(code)
        stack = []

        while pc < code_len:
            opcode = ord(code[pc])
            opcode = hint(opcode, concrete=True)
            pc += 1

            if opcode == NOP:
                pass

            elif opcode == PUSH:
                stack.append( char2int(code[pc]) )
                pc += 1

            elif opcode == POP:
                stack.pop()

            elif opcode == SWAP:
                a, b = stack.pop(), stack.pop()
                stack.append(a)
                stack.append(b)

            elif opcode == ROLL: #rotate stack top to somewhere below
                r = char2int(code[pc])
                if r < -1:
                    i = len(stack) + r
                    if i < 0:
                        raise IndexError
                    stack.insert( i, stack.pop() )
                elif r > 1:
                    i = len(stack) - r
                    if i < 0:
                        raise IndexError
                    stack.append(stack.pop(i))

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

            elif opcode == BR_COND_STK:
                offset = stack.pop()
                if stack.pop():
                    pc += hint(offset, forget=True)

            elif supports_call and opcode == CALL:
                offset = char2int(code[pc])
                pc += 1
                res = interp(code, pc + offset)
                stack.append( res )

            elif opcode == RETURN:
                break

            elif opcode == PUSHARG:
                stack.append( inputarg )

            else:
                raise RuntimeError("unknown opcode: " + str(opcode))

        return stack[-1]

    return interp


interp              = make_interp(supports_call = True)
interp_without_call = make_interp(supports_call = False)


def compile(code=''):
    bytecode = []
    labels   = {}       #[key] = pc
    label_usage = []    #(name, pc)
    for s in code.split('\n'):
        for comment in '; # //'.split():
            s = s.split(comment, 1)[0]
        s = s.strip()
        if not s:
            continue
        t = s.split()
        if t[0].endswith(':'):
            labels[ t[0][:-1] ] = len(bytecode)
            continue
        bytecode.append( tlopcode.names[ t[0] ] )
        if len(t) > 1:
            try:
                bytecode.append( int(t[1]) )
            except ValueError:
                label_usage.append( (t[1], len(bytecode)) )
                bytecode.append( 0 )
    for label, pc in label_usage:
        bytecode[pc] = labels[label] - pc - 1
    return ''.join([chr(i & 0xff) for i in bytecode])  
