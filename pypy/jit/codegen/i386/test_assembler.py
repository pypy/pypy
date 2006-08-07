from assembler import *


def test_simple():
    text, reloc = Encode([(MOV, (EAX,None), (IMM32,3000000000))])
    assert text == 'B8 00 5E D0 B2 '
    assert reloc == []

def test_jump():
    text, reloc = Encode([(JMP, 'label1'),
                          (MOV, (EAX,None), (IMM32,42)),
                          'label1',
                          (MOV, (EDX,None), (IMM32,24)),
                          ])
    assert text == 'EB 05 B8 2A 00 00 00 BA 18 00 00 00 '
    assert reloc == []

def test_jump_far():
    text, reloc = Encode([(JMP, 'label1')] +
                         [(MOV, (EAX,None), (IMM32,42))]*100 +
                         ['label1',
                          (MOV, (EDX,None), (IMM32,24)),
                          ])
    assert text == 'E9 F4 01 00 00 '+('B8 2A 00 00 00 '*100)+'BA 18 00 00 00 '
    assert reloc == []
