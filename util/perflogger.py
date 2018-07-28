import os
import sys
import logging


CRITICAL = logging.CRITICAL
FATAL = CRITICAL
ERROR = logging.ERROR
RESULT = 35
WARNING = logging.WARNING
WARN = WARNING
STATUS = 25
INFO = logging.INFO
VERBOSE = 19
VERBOSER = 18
VERBOSEST = 17
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET

custom_levels = {
    'RESULT': RESULT,
    'STATUS': STATUS,
    'VERBOSE': VERBOSE,
    'VERBOSER': VERBOSER,
    'VERBOSEST': VERBOSEST
}

for level_name, level_num in custom_levels.items():
    logging.addLevelName(level_num, level_name)

class PerfLogger(logging.Logger):

    # We use a tuple as a key (name, hash) so we can connect to the same logger instance if we have
    # multiple loggers with the same name
    perf_loggers = {}

    def __init__(self, name=None, level=NOTSET, *args, **kwargs):
        super().__init__(name, level)
        self.made_verboser = False

        PerfLogger.perf_loggers[(self.name, self.__hash__)] = self

    def make_verboser(self):
        """
        This method will increase the logging level of the stream handler and add the module and line number
        to messages if it is not present
        :return:
        """
        if not hasattr(self, 'handlers'):
            print('Can not make verboser, there are no handlers')
        else:
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

                for item in ('module', 'lineno'):
                    format_string = stream_handler.formatter._fmt

                    if item not in format_string:
                        pre, post = format_string.split('%(message)s')
                        pre = pre.rstrip().rstrip(':') + f':%({item})s '
                        _fmt = '%(message)s'.join((pre, post))

                        stream_handler.setFormatter(logging.Formatter(_fmt, stream_handler.formatter.datefmt))

        self.made_verboser = True

    def result(self, msg, *args, **kwargs):
        self._log(RESULT, msg, args, **kwargs)

    def status(self, msg, *args, **kwargs):
        self._log(STATUS, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        self._log(VERBOSE, msg, args, **kwargs)

    def verboser(self, msg, *args, **kwargs):
        self._log(VERBOSER, msg, args, **kwargs)

    def verbosest(self, msg, *args, **kwargs):
        self._log(VERBOSEST, msg, args, **kwargs)


logging.setLoggerClass(PerfLogger)


def get_perf_logger(logger_name, logger_hash, *args, **kwargs):
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


def configure_basic_logger(logger_name=None, path=None, verbose=False, stream_log_level=INFO, file_log_level=DEBUG):
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
                 *args, **kwargs):
        super().__init__(*args, *kwargs)

        if logger is None:
            # We need to make a new logger
            self.logger_name = str(type(self)).split("'")[1].split('.')[-1] if logger_name is None else logger_name
            self.logger = configure_basic_logger(logger_name=self.logger_name, stream_log_level=stream_log_level,
                                                 file_log_level=file_log_level, verbose=verbose)
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