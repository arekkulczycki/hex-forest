# -*- coding: utf-8 -*-
from abc import ABCMeta
from functools import wraps

ROUTE_ATTR = "_route"


# class route:
#     """
#     Marks a method that defines a route.
#     """
#
#     def __init__(self, url: str) -> None:
#         self.url = url
#
#     def __call__(self, target: Callable) -> Callable:
#         setattr(target, ROUTE_ATTR, self.url)
#         return target

def route(url):
    def modifier(func):
        @wraps(func)
        def wrapper(request):
            return func(request)
        setattr(wrapper, ROUTE_ATTR, url)
        return wrapper
    return modifier


class CollectRoutesMeta(ABCMeta):
    """
    Collects all methods decorated with the `route` decorator above.
    """

    def __new__(mcs, name, bases, namespace, **kwds):
        cls = type.__new__(mcs, name, bases, namespace)
        # print(inspect.getmembers(cls))
        cls._routes = [
            (value._route, value) for value in namespace.values() if hasattr(value, ROUTE_ATTR)
        ]

        for base in bases:
            if hasattr(base, "_routes"):
                cls._routes += base._routes

        return cls
