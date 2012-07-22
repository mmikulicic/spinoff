import functools


# thanks to:
# http://stackoverflow.com/questions/2589690/creating-a-method-that-is-simultaneously-an-instance-and-class-method

class combomethod(object):

    def __init__(self, method):
        self.method = method

    def __get__(self, obj=None, objtype=None):
        @functools.wraps(self.method)
        def _wrapper(*args, **kwargs):
            if obj is not None:
                return self.method(obj, *args, **kwargs)
            else:
                return self.method(objtype, *args, **kwargs)
        return _wrapper


class EnumValue(object):
    """Named value in an enumeration which can be ordered."""

    def __init__(self, name, order=None):
        self.name = name
        self.order = order

    def __lt__(self, other):
        if self.order is None or other.order is None:
            raise TypeError
        else:
            return self.order < other.order

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return '<EnumValue %s%s>' % (self.name, ':%s' % self.order if self.order is not None else '')


def enums(*names):
    """Returns a set of `EnumValue` objects with specified names and optionally orders.

    Values in an enumeration must have unique names and be either all ordered or all unordered.

    """
    if len(names) != len(list(set(names))):
        raise TypeError("Names in an enumeration must be unique")

    item_types = {True if isinstance(x, tuple) else False for x in names}
    if len(item_types) == 2:
        raise TypeError("Mixing of ordered and unordered enumeration items is not allowed")
    else:
        is_ordered = item_types.pop() is True
        if not is_ordered:
            names = [(None, x) for x in names]
        return [EnumValue(name, order) for order, name in names]


def enumrange(*names):
    """Returns an implicitly ordered enumeration.

    Shorthand for `enums((0, 'A'), (1, 'B'), (2, 'C'), ...)`

    """
    return enums(*[(order, name) for order, name in enumerate(names)])