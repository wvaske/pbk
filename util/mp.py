
import multiprocessing.queues

from Perflosophy.util.remote import SystemConnection
from Perflosophy.util.descriptors import TypeChecked


class SystemConnectionProcess(SystemConnection, multiprocessing.Process):
    """
    This baseclass will be used whenever a process needs to connect to a remote system. It verifies that the right
    connection parameters are passed and uses an instance of LogQueue to pass messages to the master logger.
    """

    log_queue = TypeChecked(multiprocessing.queues.Queue, 'log_queue', allow_none=False)

    def __init__(self, log_queue=None, *args, **kwargs):
        self.required_kwargs = [log_queue]
        super().__init__(*args, **kwargs)
        self.log_queue = log_queue
