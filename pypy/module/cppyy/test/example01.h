class payload {
public:
    payload(double d);
    payload(const payload& p);

    double getData();
    void setData(double d);

private:
    double m_data;
};


class example01 {
public:
    example01();
    example01(int a);
    example01(const example01& e);
    example01& operator=(const example01& e);
    ~example01();

public:        // class-level methods
    static int staticAddOneToInt(int a);
    static int staticAddOneToInt(int a, int b);
    static double staticAddToDouble(double a);
    static int staticAtoi(const char* str);
    static char* staticStrcpy(const char* strin);
    static void staticSetPayload(payload* p, double d);
    static payload* staticCyclePayload(payload* p, double d);
    static int getCount();

public:        // instance methods
    int addDataToInt(int a);
    double addDataToDouble(double a);
    int addDataToAtoi(const char* str);
    char* addToStringValue(const char* str);

    void setPayload(payload* p);
    payload* cyclePayload(payload* p);

public:        // class-level data
    static int count;

public:        // instance data
    int m_somedata;
};
