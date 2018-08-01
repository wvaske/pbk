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
    import pprint
    import multiprocessing

    from pbk.util.sysinfo import SystemInfoCapture
    from pbk.util.data_capture import DataCaptureManager, DummyDataCapture

    logger_name = "TestLogger"
    verbose = True
    stream_log_level = 'verboser'

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

    start_time = time.time()
    logger.debug('Creating instance of DCM')

    multiplex_params = dict(
        host=['192.168.1.15', '192.168.1.36', '192.168.1.2'],
    )

    dcm = DataCaptureManager(
        capture_classes=[SystemInfoCapture, ],
        log_queue=log_queue,
        username='root',
        password=None,
        key_filename=key_filename,
        multi_params=multiplex_params
    )

    logger.debug('Have an instance of DCM')
    logger.debug('Calling dcm.setup()')
    dcm.setup()
    logger.debug('Calling dcm.start()')

    dcm.start()
    dcm.stop()
    dcm.teardown()

    stop_time = time.time()

    for result_set in dcm.result_data:
        for capture_data in result_set['result_data']:
            capture_name = list(capture_data.keys())[0]
            logger.result(f"\n\tHost: {result_set['host']} \tCapture: {capture_name} \t"
                          f"Data : {capture_data[capture_name].keys()}\n")

    logger.result('Data capture completed in {:0.1f} seconds'.format(stop_time - start_time))

    stop_event.set()

