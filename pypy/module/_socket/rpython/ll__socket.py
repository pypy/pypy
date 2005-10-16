import _socket

def ll__socket_ntohs(htons):
    return _socket.ntohs(htons)
ll__socket_ntohs.suggested_primitive = True

def ll__socket_htons(ntohs):
    return _socket.ntohs(htons)
ll__socket_htons.suggested_primitive = True

def ll__socket_htonl(ntohl):
    return _socket.htonl(ntohl)
ll__socket_htonl.suggested_primitive = True

def ll__socket_ntohl(htonl):
    return _socket.ntohl(htonl)
ll__socket_ntohl.suggested_primitive = True
