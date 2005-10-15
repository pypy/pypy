
#ifdef MS_WINDOWS
    #include <winsock2.h>
    #include <ws2tcpip.h>
#else
    #include <arpa/inet.h>
#endif

int LL__socket_ntohs(int htons);


#ifndef PYPY_NOT_MAIN_FILE

int LL__socket_ntohs(int htons)
{

    return (int)ntohs((short) htons);

}

#endif
