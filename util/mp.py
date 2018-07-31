
import logging
import logging.handlers
import multiprocessing
import multiprocessing.queues

from Perflosophy.util.perflogger import configure_basic_logger
from Perflosophy.util.remote import send_ssh_command, SystemConnection
from Perflosophy.util.descriptors import TypeChecked


class LogQueue(multiprocessing.queues.Queue):

    def __init__(self, *args, **kwargs):
        ctx = multiprocessing.get_context()
        super(LogQueue, self).__init__(*args, **kwargs, ctx=ctx)
        self.name = 'LogQueue'

    def log(self, level, msg):
        log_object = dict(
            level=level,
            msg=msg
        )
        self.put(log_object)

    #
    # This code doesn't seem to work. I expect I can't use functools.partial like this
    #
    # def __getattribute__(self, item):
    #     perf_log_levels = ('critical', 'fatal', 'error', 'result', 'warning', 'warn', 'status',
    #                        'info', 'verbose', 'verboser', 'verbosest', 'debug')
    #     if item in perf_log_levels:
    #         print(f'Got an item in perf log levels: {item}')
    #         return functools.partial(object.__getattribute__(self, 'log'), item)
    #     else:
    #         return super().__getattribute__(item)

    def critical(self, msg):
        self.log('critical', msg)

    def fatal(self, msg):
        self.log('fatal', msg)

    def error(self, msg):
        self.log('error', msg)

    def result(self, msg):
        self.log('result', msg)

    def warning(self, msg):
        self.log('warning', msg)

    def warn(self, msg):
        self.log('warn', msg)

    def status(self, msg):
        self.log('status', msg)

    def info(self, msg):
        self.log('info', msg)

    def verbose(self, msg):
        self.log('verbose', msg)

    def verboser(self, msg):
        self.log('verboser', msg)

    def verbosest(self, msg):
        self.log('verbosest', msg)

    def debug(self, msg):
        self.log('debug', msg)

    def make_verboser(self):
        pass


class SystemConnectionProcess(SystemConnection, multiprocessing.Process):
    """
    This baseclass will be used whenever a process needs to connect to a remote system. It verifies that the right
    connection parameters are passed and uses an instance of LogQueue to pass messages to the master logger.
    """

    log_queue = TypeChecked(LogQueue, 'log_queue', allow_none=False)

    def __init__(self, log_queue=None, *args, **kwargs):
        self.required_kwargs = [log_queue]
        super().__init__(*args, **kwargs)

        self.log_queue = log_queue
        self.logger = log_queue  # Convenience to use log_queue like a logger instance
