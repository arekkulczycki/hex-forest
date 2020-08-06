def ssl_decorator(decorated_function):

    def function(obj, request, *args, **kwargs):
        request.headers['Content-Security-Policy'] = 'upgrade-insecure-requests'
        # TODO: make it work?
        # if 'https://' not in request.url:
        #     print('not secure!')
        # else:
        #     print('secure!')
        return decorated_function(obj, request, *args, **kwargs)

    return function
