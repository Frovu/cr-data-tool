import logging, traceback

def route_shielded(func):
    def wrapper():
        try:
            return func()
        except ValueError:
            return {}, 400
        except Exception:
            logging.error(f'Error in {func.__name__}: {traceback.format_exc()}')
            return {}, 500
    wrapper.__name__ = func.__name__
    return wrapper
