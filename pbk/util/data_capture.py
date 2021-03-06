import abc
import time
import logging
import logging.config
import logging.handlers
import multiprocessing
import multiprocessing.queues
import multiprocessing.managers

from pbk.util.perflogger import get_queued_logger
from pbk.util.descriptors import TypeChecked


class DataCaptureManager:

    def __init__(self, capture_classes, multi_params=None, log_queue=None, *args, **kwargs):
        """
        Data Capture Manager will build out the captures from the provided Classes, args & kwargs, and
          multi_params. multi_params should ba dictionary where the values are iterables. DCM will build
          all capture classes for each combination of params and values

          multi_params = {'host': [192.168.1.1, 192.168.1.2], 'disk': ['sda', 'sdb']}
          capture_classes = DiskInfo  #doesn't exist, but imagine if it did

          This would result in captures for:
            host: 192.168.1.1, disk: sda
            host: 192.168.1.1, disk: sdb
            host: 192.168.1.2, disk: sda
            host: 192.168.1.2, disk: sdb

          This was implemented to support captures on multiple hosts

          A user can also use add_capture_process to manually add defined capture processes. The disadvantage is
          that the capture process will need to return all pertinent data in the result_data as the multiplex
          paramater will not be recorded as it will for multi_params

        :param capture_classes:
        :param multi_params:
        :param log_queue:
        :param args:
        :param kwargs:
        """
        super().__init__()
        self.log_queue = log_queue
        self.logger = get_queued_logger(log_queue)
        self.state_sequence = ('setup', 'start', 'stop', 'teardown')

        self.args = args
        self.kwargs = kwargs
        self.captures = []
        self.capture_classes = capture_classes
        self.multi_params = multi_params
        self.capture_matrix = []

        self.logger.debug(f'Capture classes: {self.capture_classes}')
        self.logger.debug(f'Multiplexing parameters: {self.multi_params}')

        self.manager = multiprocessing.Manager()
        self.state_events = {state: multiprocessing.Event() for state in self.state_sequence}
        self.captures_states = []

        self.build_capture_processes()

    def build_capture_processes(self):
        self.capture_matrix = [{}]
        sub_matrix = []
        for param, values in self.multi_params.items():
            for value in values:
                for item in self.capture_matrix:
                    temp = item.copy()
                    temp.update({param: value})
                    sub_matrix.append(temp)

            self.capture_matrix = sub_matrix
            sub_matrix = []

        for item in self.capture_matrix:
            item['result_queue'] = multiprocessing.Queue(maxsize=len(self.capture_classes))
            item['result_data'] = []

    def setup(self, wait=True, timeout=0, daemonize=False):
        for multi_kwargs in self.capture_matrix:
            for capture_class in self.capture_classes:
                state_value = self.manager.Value('c', 'initializing')
                p = DataCaptureProcess(
                    data_capture_class=capture_class,
                    state_value=state_value,
                    state_events=self.state_events,
                    log_queue=self.log_queue,
                    *self.args,
                    **multi_kwargs,
                    **self.kwargs)

                self.logger.debug('Created instance of DCP')
                if daemonize:
                    self.logger.verbose('Daemonizing process')
                    p.daemon = True

                self.logger.debug(f'Starting dcp instance')
                p.start()
                self.logger.debug('Started dcp instance')
                self.captures.append(p)
                self.captures_states.append(state_value)

        self.state_events['setup'].set()
        if wait:
            self._wait_for_state('setuped', timeout=timeout)

    def teardown(self, wait=True, timeout=0):
        self.state_events['teardown'].set()
        if wait:
            self._wait_for_state('teardowned', timeout=timeout)

    def start(self, wait=True, timeout=0):
        self.state_events['start'].set()
        if wait:
            self._wait_for_state('started', timeout=timeout)

    def stop(self, wait=True, timeout=0):
        self.state_events['stop'].set()
        if wait:
            self._wait_for_state('stopped', timeout=timeout)

    def _wait_for_state(self, state, timeout=0):
        start_time = time.time()
        while True:
            states = self._get_states()  # Use a set to combine like states.
            if len(states) == 1 and {state}.issuperset(states):
                break
            if timeout > 0 and (time.time() - start_time >= timeout):
                self.logger.warning(f'Hit timeout of {timeout} waiting for all captures to get to state "{state}"')
            time.sleep(.5)

    def _get_states(self):
        states = {v.get() for v in self.captures_states}
        self.logger.debug(f'Got states: {states}')
        return states

    @property
    def result_data(self):
        for capture_set in self.capture_matrix:
            while capture_set['result_queue'].qsize() > 0:
                capture_set['result_data'].append(capture_set['result_queue'].get())

        result_data = []
        for capture_set in self.capture_matrix:
            result_data.append({k: v for k, v in capture_set.items() if k not in ('result_queue',)})

        return result_data


class DataCaptureProcess(multiprocessing.Process):
    """
    This class will wrap a DataCapture object in a process and execute the 4 methods based on
    event inputs (setup, start, stop, teardown). Right now these need to be executed in
    sequential order. Future work might be done to support running the functions in an arbitrary
    sequence.
    """

    log_queue = TypeChecked(multiprocessing.queues.Queue, 'log_queue', allow_none=False)

    def __init__(self, data_capture_class=None, state_value=None, state_events=None, result_queue=None, log_queue=None,
                 *args, **kwargs):
        super().__init__()

        required_kwargs = [data_capture_class, state_value, state_events, result_queue, log_queue]
        for kw in required_kwargs:
            if kw is None:
                raise ValueError(f'Keywords: {required_kwargs} are required for DataCapture classes')

        self.log_queue = log_queue

        # It's tempting to do:
        #   self.logger = ...
        #   But we can't. If we sent a self.<param> to a non-pickleable object them the Process
        #   can never start. We need to keep the log_queue and pull the logger as we need it.
        logger = get_queued_logger(log_queue)
        logger.debug(f'Args: {args}, Kwargs: {kwargs}')

        self.DataCapture = data_capture_class
        self.args = args
        self.kwargs = kwargs

        self.state_value = state_value

        self.setup_event = state_events['setup']
        self.start_event = state_events['start']
        self.stop_event = state_events['stop']
        self.teardown_event = state_events['teardown']

        self.result_queue = result_queue

    def run(self):
        logger = logging.getLogger('root')
        logger.verboser('Starting to wait for setup_event in DCP')
        self.setup_event.wait()
        logger.verboser('Got setup event in DCP')
        dc = self.DataCapture(log_queue=self.log_queue, *self.args, **self.kwargs)
        dc.setup()
        self.state_value.set('setuped')

        self.start_event.wait()
        logger.verboser('Got start event in DCP')
        dc.start()
        self.state_value.set('started')

        self.stop_event.wait()
        logger.verboser('Got stop event in DCP')
        dc.stop()
        self.state_value.set('stopped')

        self.result_queue.put(dc.data)
        logger.status('DCP put result in result queue')
        logger.debug(f'Data: {dc.data}')

        self.teardown_event.wait()
        logger.verboser('Got teardown event in DCP')
        dc.teardown()
        self.state_value.set('teardowned')
        logger.verboser('End of run() in DCP')


class DataCapture(abc.ABC):
    log_queue = TypeChecked(multiprocessing.queues.Queue, 'log_queue', allow_none=False)

    def __init__(self, log_queue=None, *args, **kwargs):
        """
        The init method of a DataCapture subclass should verify that all systems are set up for capturing data.

        Eg: A DataCapture for collectd should check that collectd is installed

        :param args:
        :param kwargs:
        """
        self._data = {}
        self.log_queue = log_queue
        self.logger = get_queued_logger(self.log_queue)

    @abc.abstractmethod
    def setup(self):
        """
        This method does any setup that we don't expect to be part of a normal system.

        Eg: A DataCapture for collectd should verify that all collects are available to run
        :return:
        """

    def teardown(self):
        """
        This method should remove any run/sequence specific files or settings from a system
        :return:
        """
        pass

    @abc.abstractmethod
    def start(self):
        """
        This method starts a data collect. Some collects will have data returned from teh start and stop and use
          the difference as the final result data. Some will only return data at the end. Regardless, start should
          NOT return data but instead hold the interim data in a file or memory structure
        :return:
        """

    def stop(self):
        """
        Stop the data collect
        :return:
        """
        pass

    @property
    def data(self):
        """
        Calling self.data will do whatever is necessary to the raw output from start and stop and return the
          'parsed/analyzed' data

        Return format:
           return {self.__name__: self._data}
        :return:
        """
        return {self.__class__.__name__: self._data}

    @data.setter
    def data(self, value):
        self._data = value


class DummyDataCapture(DataCapture):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup(self):
        self.logger.status('Setup method')

    def teardown(self):
        self.logger.status('Teardown method')

    def start(self):
        self.logger.status('Start method')

    def stop(self):
        self.logger.status('Stop method')

    @property
    def data(self):
        self.logger.status('Returning data')
        return {'data': [1, 2, 3, 4]}
