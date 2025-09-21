# decorators.py
from functools import wraps


def validator(fn):
    """No-op validator decorator that preserves function metadata and
    marks the function for detection by the parser.
    """
    @wraps(fn)
    def _wrapper(*args, **kwargs):
        return fn(*args, **kwargs)


    # mark the wrapped function so other tools can detect it reliably
    setattr(_wrapper, "__pyken_validator__", True)
    return _wrapper