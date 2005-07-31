
#define STANDALONE_ENTRY_POINT   PYPY_STANDALONE

int main(int argc, char *argv[])
{
    int i;
    RPyListOfString *list = RPyListOfString_New(argc);
    for (i=0; i<argc; i++) {
        RPyString *s = RPyString_FromString(argv[i]);
        RPyListOfString_SetItem(list, i, s);
    }
    return STANDALONE_ENTRY_POINT(list);
}

