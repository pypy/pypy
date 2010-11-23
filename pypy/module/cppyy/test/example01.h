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
    static int count;
    int m_somedata;

    example01();
    example01(int a);
    example01(const example01& e);
    example01& operator=(const example01& e);
    ~example01();

// class methods
    static int staticAddOneToInt(int a);
    static int staticAddOneToInt(int a, int b);
    static double staticAddToDouble(double a);
    static int staticAtoi(const char* str);
    static char* staticStrcpy(const char* strin);
    static void staticSetPayload(payload* p, double d);
    static payload* staticCyclePayload(payload* p, double d);
    static int getCount();

// instance methods
    int addDataToInt(int a);
    double addDataToDouble(double a);
    int addDataToAtoi(const char* str);
    char* addToStringValue(const char* str);

    void setPayload(payload* p);
    payload* cyclePayload(payload* p);
};
