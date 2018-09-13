/* # of bytes for year, month, and day. */
#define _PyDateTime_DATE_DATASIZE 4

/* # of bytes for hour, minute, second, and usecond. */
#define _PyDateTime_TIME_DATASIZE 6

/* # of bytes for year, month, day, hour, minute, second, and usecond. */
#define _PyDateTime_DATETIME_DATASIZE 10

/* "magic" constant used to partially protect against developer mistakes. */
#define DATETIME_API_MAGIC 0x414548d5

/* Define structure for C API. */
typedef struct {
    /* type objects */
    PyTypeObject *DateType;
    PyTypeObject *DateTimeType;
    PyTypeObject *TimeType;
    PyTypeObject *DeltaType;
    PyTypeObject *TZInfoType;

    /* constructors */
    PyObject *(*Date_FromDate)(int, int, int, PyTypeObject*);
    PyObject *(*DateTime_FromDateAndTime)(int, int, int, int, int, int, int,
        PyObject*, PyTypeObject*);
    PyObject *(*Time_FromTime)(int, int, int, int, PyObject*, PyTypeObject*);
    PyObject *(*Delta_FromDelta)(int, int, int, int, PyTypeObject*);
    PyObject *(*TimeZone_FromTimeZone)(PyObject *offset, PyObject *name);

    PyObject *(*DateTime_FromTimestamp)(PyObject*, PyObject*, PyObject*);
    PyObject *(*Date_FromTimestamp)(PyObject*, PyObject*);

        PyObject *(*DateTime_FromDateAndTimeAndFold)(int, int, int, int, int, int, int,
        PyObject*, int, PyTypeObject*);
    PyObject *(*Time_FromTimeAndFold)(int, int, int, int, PyObject*, int, PyTypeObject*);
} PyDateTime_CAPI;

typedef struct
{
    PyObject_HEAD
    long hashcode;
    int days;                   /* -MAX_DELTA_DAYS <= days <= MAX_DELTA_DAYS */
    int seconds;                /* 0 <= seconds < 24*3600 is invariant */
    int microseconds;           /* 0 <= microseconds < 1000000 is invariant */
} PyDateTime_Delta;

/* The datetime and time types have an optional tzinfo member,
 * PyNone if hastzinfo is false.
 */
typedef struct
{
    PyObject_HEAD
    unsigned char hastzinfo;
    PyObject *tzinfo;
} PyDateTime_Time; /* hastzinfo true */

typedef struct 
{
    PyObject_HEAD
    long hashcode;
    char hastzinfo;
    unsigned char data[_PyDateTime_TIME_DATASIZE];
} PyDateTime_BaseTime; /* hastzinfo false */

typedef struct 
{
    PyObject_HEAD
    long hashcode;
    char hastzinfo;
    unsigned char data[_PyDateTime_DATETIME_DATASIZE];
} PyDateTime_BaseDateTime; /* hastzinfo false */

typedef struct
{
    PyObject_HEAD
    long hashcode;
    unsigned char hastzinfo;
    unsigned char fold;
    PyObject *tzinfo;
    unsigned char data[_PyDateTime_DATETIME_DATASIZE];
} PyDateTime_DateTime; /* hastzinfo true */


typedef struct {
    PyObject_HEAD
    long hashcode;
    char hastzinfo;
    unsigned char data[_PyDateTime_DATE_DATASIZE];
} PyDateTime_Date;


typedef struct {
    PyObject_HEAD
} PyDateTime_TZInfo;

typedef struct 
{
    PyObject_HEAD
    long hashcode;
    char hastzinfo;
} _PyDateTime_BaseTZInfo;


