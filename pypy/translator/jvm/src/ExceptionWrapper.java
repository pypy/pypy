package pypy;

public class ExceptionWrapper extends RuntimeException {
    public final Object object;

    ExceptionWrapper (Object object) {
        this.object = object;
    }

    public static ExceptionWrapper wrap(Object object) {
        return new ExceptionWrapper(object);
    }
}