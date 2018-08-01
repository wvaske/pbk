import time
import logging
import logging.config
import logging.handlers

from pbk.util.perflogger import configure_basic_logger, get_queued_logger


def log_queue_listener(q, stop_event, logger_name, **kwargs):
    logger = configure_basic_logger(logger_name, **kwargs)
    logger.info(f'Got a logger with name: {logger.name} and hash: {logger.__hash__()}. Messages from the queue'
                f'will be handled by this logger.')
    listener = logging.handlers.QueueListener(q, *logger.handlers, respect_handler_level=True)
    listener.start()
    logger.verbose('Log queue listener is started and waiting for stop event')
    stop_event.wait()
    logger.verbose('Log queue listener got stop event, stopping listener...')
    listener.stop()


if __name__ == "__main__":

    import multiprocessing

    from pbk.util.p_sysinfo import SystemInfoCapture
    from pbk.util.p_data_capture import DataCaptureManager, DummyDataCapture

    logger_name = "TestLogger"
    verbose = False
    stream_log_level = None

    stop_event = multiprocessing.Event()
    log_queue = multiprocessing.Queue()

    listener_kwargs = dict(verbose=verbose)
    if stream_log_level is not None:
        listener_kwargs['stream_log_level'] = stream_log_level

    listener_process = multiprocessing.Process(target=log_queue_listener, name="Listener",
                                               args=(log_queue, stop_event, logger_name),
                                               kwargs=listener_kwargs)
    listener_process.start()

    logger = get_queued_logger(log_queue)
    logger.debug('Test message #1')

    auto_get = True
    key_filename = r'c:\Users\Administrator\Desktop\dev_sys_key.pem'
    auth = dict(host='192.168.1.15', username='root', key_filename=key_filename, password=None)

    logger.debug('Creating instance of DCM')
    dcm = DataCaptureManager(
        capture_classes=[SystemInfoCapture, ],
        log_queue=log_queue,
        host='192.168.1.15',
        username='root',
        password=None,
        key_filename=key_filename
    )

    logger.debug('Have an instance of DCM')
    logger.debug('Calling dcm.setup()')
    dcm.setup()
    logger.debug('Calling dcm.start()')
    dcm.start()
    dcm.logger.debug('We started things')
    dcm.stop()
    dcm.teardown()

    logger.result(f'Data is: {dcm.result_data}')

    stop_event.set()
    exit()
