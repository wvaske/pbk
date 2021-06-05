import os
import sys
import logging
import logging.config
import logging.handlers

CRITICAL = logging.CRITICAL
FATAL = CRITICAL
ERROR = logging.ERROR
RESULT = 35
WARNING = logging.WARNING   # 30
WARN = WARNING
STATUS = 25
INFO = logging.INFO         # 20
VERBOSE = 19
VERBOSER = 18
VERBOSEST = 17
DEBUG = logging.DEBUG       # 10
RIDICULOUS = 7
LUDICROUS = 5
PLAID = 3
NOTSET = logging.NOTSET

custom_levels = {
    'RESULT': RESULT,
    'STATUS': STATUS,
    'VERBOSE': VERBOSE,
    'VERBOSER': VERBOSER,
    'VERBOSEST': VERBOSEST,
    'RIDICULOUS': RIDICULOUS,
    'LUDICROUS': LUDICROUS,
    'PLAID': PLAID
}

for level_name, level_num in custom_levels.items():
    logging.addLevelName(level_num, level_name)


def get_queued_logger(log_queue):
    queued_logger = PerfLogger('Perf')
    queue_handler = logging.handlers.QueueHandler(log_queue)
    queued_logger.addHandler(queue_handler)
    return queued_logger


class PerfLogger(logging.Logger):
    # We use a tuple as a key (name, hash) so we can connect to the same logger instance if we have
    # multiple loggers with the same name
    perf_loggers = {}

    def __init__(self, name=None, level=NOTSET, *args, **kwargs):
        super().__init__(name, level)
        self.made_verboser = False

        PerfLogger.perf_loggers[(self.name, self.__hash__())] = self

    def __reduce__(self):
        return get_perf_logger, (self.name,)
    
    def make_verboser(self):
        """
        This method will increase the logging level of the stream handler and add the module and line number
        to messages if it is not present
        :return:
        """
        if not hasattr(self, 'handlers'):
            print('Can not make verboser, there are no handlers')
        else:
            self.warning('Making VERBOSER')
            stream_handlers = [h for h in self.handlers if not hasattr(h, 'baseFilename')]
            log_levels = sorted([v for k, v in sys.modules[__name__].__dict__.items() if type(v) is int])

            for stream_handler in stream_handlers:
                if stream_handler.level > VERBOSE:
                    stream_handler.setLevel(VERBOSE)
                else:
                    current_level_index = log_levels.index(stream_handler.level)
                    if current_level_index <= 1:
                        stream_handler.setLevel(0)
                    else:
                        stream_handler.setLevel(log_levels[current_level_index - 1])

                for item in ('processName', 'module', 'lineno'):
                    format_string = stream_handler.formatter._fmt

                    if item not in format_string:
                        pre, post = format_string.split('%(message)s')
                        pre = pre.rstrip().rstrip(':') + f':%({item})s '
                        _fmt = '%(message)s'.join((pre, post))

                        stream_handler.setFormatter(logging.Formatter(_fmt, stream_handler.formatter.datefmt))
                self.info(f'New stream log level: {stream_handler.level}')

        self.made_verboser = True

    # def _log(self, level, msg, args, color=None, exc_info=None, extra=None, stack_info=False):
    #     # At one point I had log in _log and called super() to modify messages. For some reason
    #     #   that doesn't work and I'm not entirely sure why. I ended up removing that particular
    #     #   functionality but I'm leaving this here and commented out in case I implement some
    #     #   other message formatting down the road and then don't need to figure this out
    #     #   all over again.
    #     #
    #     # To get _log to work properly (especially for module and line number) we just copy and
    #     #   this content from the base class and reimplement it here. There's probably a way to
    #     #   get the traceback to properly go up a level but I couldn't figure it out and this
    #     #   was pretty easy
    #
    #     #
    #     #  Insert future message modifications here
    #     #
    #
    #     # Keep this part due to the message above
    #     sinfo = None
    #     fn, lno, func, sinfo = self.findCaller(stack_info)
    #     if exc_info:
    #         if isinstance(exc_info, BaseException):
    #             exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
    #         elif not isinstance(exc_info, tuple):
    #             exc_info = sys.exc_info()
    #     record = self.makeRecord(self.name, level, fn, lno, msg, args, exc_info, func, extra, sinfo)
    #     self.handle(record)

    def error(self, msg, *args, **kwargs):
        self._log(ERROR, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log(WARNING, msg, *args, **kwargs)

    def result(self, msg, *args, **kwargs):
        self._log(RESULT, msg, args, **kwargs)

    def status(self, msg, *args, **kwargs):
        self._log(STATUS, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log(INFO, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        self._log(VERBOSE, msg, args, **kwargs)

    def verboser(self, msg, *args, **kwargs):
        self._log(VERBOSER, msg, args, **kwargs)

    def verbosest(self, msg, *args, **kwargs):
        self._log(VERBOSEST, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log(DEBUG, msg, args, **kwargs)

    def ridiculous(self, msg, *args, **kwargs):
        self._log(RIDICULOUS, msg, args, **kwargs)

    def ludicrous(self, msg, *args, **kwargs):
        self._log(LUDICROUS, msg, args, **kwargs)

    def plaid(self, msg, *args, **kwargs):
        self._log(PLAID, msg, args, **kwargs)

    def log_queue_writer(self, level, msg):
        level_method = getattr(self, level.lower())
        level_method(msg)


logging.setLoggerClass(PerfLogger)


def get_perf_logger(logger_name, logger_hash=None, *args, **kwargs):
    if (logger_name, logger_hash) not in PerfLogger.perf_loggers.keys():
        # if we can't find the specific by name & hash, try to find one by name only
        # If there are multiple loggers with the same name, this will pull a 'random' one
        loggers_by_names = {k[0]: v for k, v in PerfLogger.perf_loggers.items()}
        if logger_name in loggers_by_names.keys():
            logger = loggers_by_names[logger_name]
            logger.error(f'Not able to find an existing logger with name and hash: {logger_name} & {logger_hash}')
            logger.error(f'Found another logger by same name')
        else:
            logger = configure_basic_logger(logger_name=logger_name, *args, **kwargs)
            logger.error(f'Not able to find an existing logger with name: {logger_name}')
            logger.error(f'Created a new logger')
        return logger
    else:
        return PerfLogger.perf_loggers[(logger_name, logger_hash)]


def configure_basic_logger(logger_name=None, path=None, verbose=False,
                           stream_log_level=INFO, file_log_level=DEBUG, **kwargs):
    if isinstance(stream_log_level, str):
        stream_log_level = logging.getLevelName(stream_log_level.upper())
    if isinstance(file_log_level, str):
        file_log_level = logging.getLevelName(file_log_level.upper())

    logger = PerfLogger(logger_name)
    logger.setLevel(file_log_level)

    log_file_name = '{}.log'.format(logger_name.rstrip('.log'))
    if not path:
        if sys.platform.startswith('win'):
            path = 'c:\\temp'
        elif sys.platform.startswith('linux'):
            path = '/var/log'

    log_file = os.path.join(path, log_file_name)

    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter('%(asctime)s|%(levelname)s: %(message)s', '%H:%M:%S')
    stream_handler.setFormatter(stream_formatter)
    stream_handler.setLevel(stream_log_level)
    logger.addHandler(stream_handler)

    try:
        file_handler = logging.FileHandler(log_file, mode='a')
    except IOError as e:
        print(f'Cannot access log file: {log_file_name} in path: {path}. Verify this user has permissions on the'
              f'directory or use a different path')
        raise e

    file_formatter = logging.Formatter('%(asctime)s|%(levelname)s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(file_log_level)
    logger.addHandler(file_handler)

    if verbose:
        logger.make_verboser()

    return logger


class LoggedObject(object):

    def __init__(self, logger_name=None, logger=None, verbose=False, stream_log_level=INFO, file_log_level=DEBUG,
                 log_queue=None, *args, **kwargs):
        super().__init__()

        self.log_queue = log_queue
        if self.log_queue:
            self.logger = get_queued_logger(log_queue)
            self.logger.verbose(f'Using queued logger from log_queue: {self.log_queue}')
            self.logger_name = self.logger.name
        elif logger is None:
            # We need to make a new logger
            self.logger_name = str(type(self)).split("'")[1].split('.')[-1] if logger_name is None else logger_name
            self.logger = configure_basic_logger(logger_name=self.logger_name, stream_log_level=stream_log_level,
                                                 file_log_level=file_log_level, verbose=verbose)
            self.logger.warning('We made a new logger')
        else:
            self.logger = logger
            self.logger_name = logger.name
            if verbose:
                try:
                    self.logger.make_verboser()
                except AttributeError:
                    self.logger.error("Got 'verbose' flag but logger doesn't support 'make_verboser' method. "
                                      "Leaving handlers alone and not making verboser")


if __name__ == '__main__':
    logger = configure_basic_logger('test_logger', stream_log_level='info', file_log_level='debug')
    logger.debug('test')
    logger.make_verboser()
    logger.debug('test post make verboser')
