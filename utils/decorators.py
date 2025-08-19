from functools import wraps


def session_required(fn):
    @wraps(fn)
    async def wrapper(self_or_cls, session=None, *args, **kwargs):
        if session is None:
            session = self_or_cls.get_session()
        return await fn(self_or_cls, session, *args, **kwargs)

    return wrapper
