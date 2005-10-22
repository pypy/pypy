
#ifdef MS_WINDOWS
# pragma comment(lib, "ws2_32.lib")
#else
# include <arpa/inet.h>
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

RPyString *LL__socket_gethostname()
{
	char buf[1024];
	char *res;
	res = gethostname(buf, sizeof buf - 1);
	if (res < 0) {
		//XXX
		//RPYTHON_RAISE_OSERROR(errno);
		RPyRaiseSimpleException(PyExc_ValueError,
					"gethostname() error");
		return NULL;
	}
	buf[sizeof buf - 1] = '\0';
	return RPyString_FromString(buf);
}

#endif
