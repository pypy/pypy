opcode = 0
def next_opcode():
    global opcode
    opcode += 1
    return opcode

PUSH    = next_opcode()   #1 operand
POP     = next_opcode()
SWAP    = next_opcode()
ROT     = next_opcode()

PICK    = next_opcode()   #1 operand (DUP = PICK,0)
PUT     = next_opcode()   #1 operand

ADD     = next_opcode()
SUB     = next_opcode()
MUL     = next_opcode()
DIV     = next_opcode()

EQ      = next_opcode()
NE      = next_opcode()
LT      = next_opcode()
LE      = next_opcode()
GT      = next_opcode()
GE      = next_opcode()

BR_COND = next_opcode()  #1 operand offset

CALL    = next_opcode()  #1 operand offset
RETURN  = next_opcode()

EXIT    = next_opcode()

INVALID = next_opcode()
