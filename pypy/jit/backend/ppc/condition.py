# CONDITION = (BI (number of bit tested in CR), BO (12 if bit is 1, else 4))

SET   = 12
UNSET = 4

LE = (1, UNSET)
NE = (2, UNSET)
GT = (1, SET)
LT = (0, SET)
EQ = (2, SET)
GE = (0, UNSET)

# values below are random ...

U_LT = 50
U_LE = 60
U_GT = 70
U_GE = 80

IS_TRUE = 90
IS_ZERO = 100
