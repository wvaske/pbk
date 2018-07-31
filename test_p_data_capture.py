import time
import logging
import logging.config
import logging.handlers

from Perflosophy.util.perflogger import configure_basic_logger, queued_logger_config


def log_queue_listener(q, stop_event, logger_name, **kwargs):
    logger = configure_basic_logger(logger_name, **kwargs)
    logger.info(f'Got a logger with name: {logger.name} and hash: {logger.__hash__()}')
    listener = logging.handlers.QueueListener(q, *logger.handlers, respect_handler_level=True)
    listener.start()
    logger.status('Waiting for stop event')
    stop_event.wait()
    logger.status('Got stop event, stopping listener...')
    listener.stop()


if __name__ == "__main__":

    import multiprocessing

    from Perflosophy.util.p_sysinfo import SystemInfoCapture
    from Perflosophy.util.p_data_capture import DataCaptureManager, DummyDataCapture

    logger_name = "TestLogger"
    stop_event = multiprocessing.Event()
    log_queue = multiprocessing.Queue()
    listener_process = multiprocessing.Process(target=log_queue_listener, name="Listener",
                                               args=(log_queue, stop_event, logger_name), kwargs=dict(verbose=True))
    listener_process.start()

    logging.config.dictConfig(queued_logger_config(log_queue))
    logger = logging.getLogger('root')
    logger.info('Test message, sleeping 1s')
    time.sleep(1)

    verbose = False
    auto_get = True
    key_filename = r'c:\Users\Administrator\Desktop\dev_sys_key.pem'
    auth = dict(host='192.168.1.15', username='root', key_filename=key_filename, password=None)

    logger.info('Creating instance of DCM')
    dcm = DataCaptureManager(
        capture_classes=[SystemInfoCapture, ],
        log_queue=log_queue,
        host='192.168.1.15',
        username='root',
        password=None,
        key_filename=key_filename,
        stream_log_level='info'
    )

    logger.info('Have an instance off DCM, sleeping 1')
    time.sleep(1)
    logger.info('Calling dcm.setup()')
    dcm.setup()
    logger.info('Calling dcm.start()')
    dcm.start()
    dcm.logger.info('We started things')
    dcm.stop()
    dcm.teardown()

    logger.result(f'Data is: {dcm.result_data}')

    stop_event.set()
    exit()
