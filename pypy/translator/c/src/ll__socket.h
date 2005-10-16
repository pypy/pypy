
#ifdef MS_WINDOWS
    #include <winsock2.h>
    #include <ws2tcpip.h>
#else
    #include <arpa/inet.h>
#endif

int LL__socket_ntohs(int htons);
int LL__socket_htons(int ntohs);
long LL__socket_ntohl(long htonl);
long LL__socket_htonl(long ntohl);

#ifndef PYPY_NOT_MAIN_FILE

int LL__socket_ntohs(int htons)
{

    return (int)ntohs((short) htons);

}

int LL__socket_htons(int ntohs)
{

    return (int)htons((short) ntohs);

}

long LL__socket_ntohl(long htonl)
{

    return ntohl(htonl);

}

long LL__socket_htonl(long ntohl)
{

    return htonl(ntohl);

}

#endif
