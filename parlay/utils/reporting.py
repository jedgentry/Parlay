import traceback
import logging


logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)  # use this as the logger


def log_stack_on_error(deferred, msg=""):
    """
    Add an errback to the given deferred object to display the
    current stack trace as an aid for user debugging.

    :param deferred: Twisted Deferred object to add errback to
    :param msg: optional error message to display before the stack trace
    :type msg: str
    :return: Deferred

    **Example Usage**::

        def myFunc():
            d = async_function_that_returns_deferred()

            # will show stack trace of myFunc and its callers
            d = log_stack_on_error(d, msg=")

            return d

    """

    stack = traceback.format_stack()
    stack = stack[:-2]  # remove last 2 stack function calls -- 2nd to last is this function, last is format_stack

    stack_str = ""
    for item in stack:
        stack_str += item

    def errback(failure):
        error_message = "\n=========================="
        error_message += "\nERROR: An asynchronous function threw the following exception:\n\n"
        error_message += failure.getBriefTraceback()
        error_message += "\n"
        error_message += msg
        error_message += "\n\nORIGINAL CALL STACK THAT LED TO ERROR:\n\n"
        error_message += stack_str
        error_message += "\n==========================\n\n"

        logger.error(error_message)

    deferred.addErrback(errback)
    return deferred
