from pypy.rlib.rarithmetic import LONG_BIT

# ___________________________________________________________________________
# Slot Names

CHARACTER_VALUE_INDEX = 0        # Page 630 of the blue book

STREAM_ARRAY_INDEX = 0           # Page 631 of the blue book
STREAM_INDEX_INDEX = 1
STREAM_READ_LIMIT_INDEX = 2
STREAM_WRITE_LIMIT_INDEX = 3

CLASS_SUPERCLASS_INDEX = 0
CLASS_METHODDICT_INDEX = 1
CLASS_FORMAT_INDEX = 2
CLASS_NAME_INDEX = 6                # in the mini.image, at least

# MethodDict
METHODDICT_TALLY_INDEX = 0
METHODDICT_VALUES_INDEX = 1
METHODDICT_NAMES_INDEX  = 2

# Message
MESSAGE_SELECTOR_INDEX = 0
MESSAGE_ARGUMENTS_INDEX = 1
MESSAGE_LOOKUP_CLASS_INDEX = 2

# ContextPart
CTXPART_SENDER_INDEX = 0
CTXPART_PC_INDEX = 1
CTXPART_STACKP_INDEX = 2

METHOD_HEADER_INDEX = 0

# BlockContext < ContextPart
BLKCTX_BLOCK_ARGUMENT_COUNT_INDEX = 3
BLKCTX_INITIAL_IP_INDEX = 4
BLKCTX_HOME_INDEX = 5
BLKCTX_STACK_START = 6

# MethodContext < ContextPart
MTHDCTX_METHOD = 3
MTHDCTX_RECEIVER_MAP = 4
MTHDCTX_RECEIVER = 5
MTHDCTX_TEMP_FRAME_START = 6

# ___________________________________________________________________________
# Miscellaneous constants

LITERAL_START = 1 # index of the first literal after the method header
BYTES_PER_WORD = 4

# ___________________________________________________________________________
# Special objects indices

SO_NIL = 0
SO_FALSE = 1
SO_TRUE = 2
SO_SCHEDULERASSOCIATIONPOINTER = 3
SO_BITMAP_CLASS = 4
SO_SMALLINTEGER_CLASS = 5
SO_STRING_CLASS = 6
SO_ARRAY_CLASS = 7
SO_SMALLTALK = 8
SO_FLOAT_CLASS = 9
SO_METHODCONTEXT_CLASS = 10
SO_BLOCKCONTEXT_CLASS = 11
SO_POINT_CLASS = 12
SO_LARGEPOSITIVEINTEGER_CLASS = 13
SO_DISPLAY_CLASS = 14
SO_MESSAGE_CLASS = 15
SO_COMPILEDMETHOD_CLASS = 16
SO_LOW_SPACE_SEMAPHORE = 17
SO_SEMAPHORE_CLASS = 18
SO_CHARACTER_CLASS = 19
SO_DOES_NOT_UNDERSTAND = 20
SO_CANNOT_RETURN = 21

# XXX no clue what 22 is doing, lookup in Squeak: ObjectMemory >> initializeSpecialObjectIndices

SO_SPECIAL_SELECTORS_ARRAY = 23
SO_CHARACTER_TABLE_ARRAY = 24
SO_MUST_BE_BOOLEAN = 25
SO_BYTEARRAY_CLASS = 26
SO_PROCESS_CLASS = 27
SO_COMPACT_CLASSES_ARRAY = 28
SO_DELAY_SEMAPHORE = 29
SO_USER_INTERRUPT_SEMAPHORE = 30
SO_FLOAT_ZERO = 31
SO_LARGEPOSITIVEINTEGER_ZERO = 32
SO_A_POINT = 33
SO_CANNOT_INTERPRET = 34
SO_A_METHODCONTEXT = 35
# no clue what 36 is doing
SO_A_BLOCKCONTEXT = 37
SO_AN_ARRAY = 38
SO_PSEUDOCONTEXT_CLASS = 39
SO_TRANSLATEDMETHOD_CLASS = 40
SO_FINALIZATION_SEMPAHORE = 41
SO_LARGENEGATIVEINTEGER_CLASS = 42

# XXX more missing?
classes_in_special_object_table = {
#    "Bitmap" : SO_BITMAP_CLASS,
    "SmallInteger" : SO_SMALLINTEGER_CLASS,
    "String" : SO_STRING_CLASS,
    "Array" : SO_ARRAY_CLASS,
    "Float" : SO_FLOAT_CLASS,
    "MethodContext" : SO_METHODCONTEXT_CLASS,
    "BlockContext" : SO_BLOCKCONTEXT_CLASS,
    "Point" : SO_POINT_CLASS,
    "LargePositiveInteger" : SO_LARGEPOSITIVEINTEGER_CLASS,
#    "Display" : SO_DISPLAY_CLASS,
#    "Message" : SO_MESSAGE_CLASS,
    "CompiledMethod" : SO_COMPILEDMETHOD_CLASS,
    "Semaphore" : SO_SEMAPHORE_CLASS,
    "Character" : SO_CHARACTER_CLASS,
    "ByteArray" : SO_BYTEARRAY_CLASS,
    "Process" : SO_PROCESS_CLASS,
#    "PseudoContext" : SO_PSEUDOCONTEXT_CLASS,
#    "TranslatedMethod" : SO_TRANSLATEDMETHOD_CLASS,
    # "LargeNegativeInteger" : SO_LARGENEGATIVEINTEGER_CLASS, # Not available in mini.image
}

objects_in_special_object_table = {
    "nil": SO_NIL,
    "true": SO_TRUE,
    "false": SO_FALSE,
    "charactertable": SO_CHARACTER_TABLE_ARRAY,
    "schedulerassociationpointer" : SO_SCHEDULERASSOCIATIONPOINTER,
    "smalltalkdict" : SO_SMALLTALK,
}

TAGGED_MAXINT = 2 ** (LONG_BIT - 2) - 1
TAGGED_MININT = -2 ** (LONG_BIT - 2)
