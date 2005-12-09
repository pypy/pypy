g_opcode = 0
names = {}

def opcode(opcode_name):
    global g_opcode, opcode_names
    g_opcode += 1
    names[opcode_name] = globals()[opcode_name] = g_opcode

opcode("PUSH")     #1 operand
opcode("POP")
opcode("SWAP")
opcode("ROT")

opcode("PICK")     #1 operand (DUP = PICK,0)
opcode("PUT")      #1 operand

opcode("ADD")
opcode("SUB")
opcode("MUL")
opcode("DIV")

opcode("EQ")
opcode("NE")
opcode("LT")
opcode("LE")
opcode("GT")
opcode("GE")

opcode("BR_COND")  #1 operand offset

opcode("CALL")  #1 operand offset
opcode("RETURN")

opcode("EXIT")

opcode("INVALID")

del opcode
del g_opcode
