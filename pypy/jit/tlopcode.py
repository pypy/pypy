names = {}

def opcode(n, opcode_name):
    global opcode_names
    names[opcode_name] = globals()[opcode_name] = n

opcode(1,  "NOP")
opcode(2,  "PUSH")     #1 operand
opcode(3,  "POP")
opcode(4,  "SWAP")
opcode(5,  "ROT")

opcode(6,  "PICK")     #1 operand (DUP = PICK,0)
opcode(7,  "PUT")      #1 operand

opcode(8,  "ADD")
opcode(9,  "SUB")
opcode(10, "MUL")
opcode(11, "DIV")

opcode(12, "EQ")
opcode(13, "NE")
opcode(14, "LT")
opcode(15, "LE")
opcode(16, "GT")
opcode(17, "GE")

opcode(18, "BR_COND")  #1 operand offset
opcode(19, "BR_COND_STK")    # no operand, takes [condition, offset] from the stack

opcode(20, "CALL")  #1 operand offset
opcode(21, "RETURN")

opcode(22, "INVALID")

del opcode
