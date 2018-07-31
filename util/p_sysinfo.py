#!/usr/bin/env python3.6

import sys
import time
import logging
import logging.config
import functools
import multiprocessing

from Perflosophy.util.mp import LogQueue, SystemConnectionProcess
from Perflosophy.util.remote import send_ssh_command, linux_which
from Perflosophy.util.perflogger import LoggedObject, queued_logger_config
from Perflosophy.util.p_data_capture import DataCapture


class SystemInfo(LoggedObject):

    def __init__(self, host, username, password=None, key_filename=None, auto_get=False, *args, **kwargs):
        """
        This class will connect to a system (currently linux only) and run various system tools
        to get system information.

        The auto_get flag is enabled by following specific conventions for method nameing:
            Methods should be named like "get_<linux tool name>"
            The method will use generic parsing functions outside of this class
            The method will set the value of self.system_info[<linux tool name>]
            The method will ALSO return the data it assigns to system_info
        :param host:
        :param username:
        :param password:
        :param key_filename:
        :param auto_get:
        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.system_info = {}
        self.auth = dict(host=host, username=username, password=password, key_filename=key_filename)
        self.send_command = functools.partial(send_ssh_command, **self.auth)

        self.prerequisites = []
        self.get_classes = [v for k, v in sys.modules[__name__].__dict__.items()
                            if k.startswith('Get')
                            and issubclass(v, GetInfo)
                            and k != 'GetInfo']

        for cls in self.get_classes:
            self.prerequisites.extend(cls.prerequisites)

        self.logger.info(f'System info prerequisites: {self.prerequisites}')
        for prereq in self.prerequisites:
            if linux_which(prereq, host, username, password, key_filename) is None:
                self.logger.warning(f'Prerequisite "{prereq}" is not met')

        if auto_get:
            self.logger.status(f'Getting data from all possible sources on host {host}')
            self.get_all()

    def get_all(self):
        process_pool = []
        data_queue = multiprocessing.Queue()
        log_queue = LogQueue()
        for cls in self.get_classes:
            process_pool.append(cls(data_queue, **self.auth, log_queue=log_queue))

        for p in process_pool:
            p.daemon = True
            self.logger.info(f'Started process: {p.name}')

        [p.start() for p in process_pool]

        # We can join and read all, or we can poll queue until we get the number we expect.
        # If we join, we can have some processes that exit without returning data. If we poll
        # the queue then we need each process to put _something_ in the queue or we hang forever

        # Additionally, now that I added logger_queue, we don't want to .join because we want to
        # pull log messages and log them as we get them.

        while data_queue.qsize() != len(self.get_classes) or not log_queue.empty():
            self.logger.verbose('Checking log queue')
            while not log_queue.empty():
                self.logger.verboser('Have messages in log_queue')
                msg = log_queue.get()
                self.logger.log_queue_writer(**msg)
            self.logger.verboser('Do not have data from each process...sleeping')
            time.sleep(.5)

        for i in range(len(self.get_classes)):
            self.system_info.update(data_queue.get())

        self.logger.status('Joining')
        [p.join() for p in process_pool]
        self.logger.status('Done!')


class GetInfo(SystemConnectionProcess):

    def __init__(self, result_queue=None, *args, **kwargs):
        self.required_kwargs = [result_queue]
        super().__init__(*args, **kwargs)
        self.result_queue = result_queue


class GetDmidecode(GetInfo):

    prerequisites = ['dmidecode', 'doesnotexist']

    def run(self):
        stdout, stderr = self.send_command('dmidecode')
        self.logger.verbose(f'stdout length: {len(stdout)}')
        self.logger.verboser(f'Parsing dmidecode stdout:\n {stdout}')
        if stdout is "":
            self.logger.error('Did not get data for dmidecode command')
            return None
        else:
            self.logger.verbose('Beginning parse of dmidecode')
            self.logger.verboser(f'Repr of stdout: {repr(stdout)}')
            parsed_dmi = parse_dmidecode_output(stdout)
            self.result_queue.put({'dmidecode': parsed_dmi})
            self.logger.verbose(f'dmidecode returned {len(parsed_dmi.keys())} sections')
            return parsed_dmi


def parse_dmidecode_output(content):
    """
    Parse the whole dmidecode output.
    Returns a list of tuples of (type int, value dict).
    """
    dmi_type = {
        0: 'bios',
        1: 'system',
        2: 'base board',
        3: 'chassis',
        4: 'processor',
        7: 'cache',
        8: 'port connector',
        9: 'system slot',
        10: 'on board device',
        11: 'OEM strings',
        # 13: 'bios language',
        15: 'system event log',
        16: 'physical memory array',
        17: 'memory_device',
        19: 'memory array mapped address',
        24: 'hardware security',
        25: 'system power controls',
        27: 'cooling device',
        32: 'system boot',
        41: 'onboard device',
    }

    info = {}
    sections = content.split('\n\n')
    sections = [section.splitlines() for section in sections]

    info = {_type: {} for _type in dmi_type.values()}

    for section in sections[1:]:
        # Skip the first 'section' as it isn't a real section
        header = section[0]
        if header.startswith('Handle 0x'):
            handle = header.split(',')[0][len('Handle '):]
            _type = int(header.split(',', 2)[1].strip()[len('DMI type'):])
            if _type == 127:
                break
            if _type in dmi_type:
                section_data = _parse_dmi_section(section[1:])
                section_data['_handle'] = handle
                info[dmi_type[_type]] = section_data

    return info


def _parse_dmi_section(section):
    data = {'_title': section[0].strip()}

    for line in section[1:]:
        line = line.rstrip()
        if line.startswith('\t\t'):
            # We only get a \t\t after we have already parsed a line that starts
            # with \t. Therefore we know that k is set when we get here from the
            # previous line.
            data[k].append(line.lstrip())
        elif line.startswith('\t'):
            k, v = [i.strip() for i in line.lstrip().split(':', 1)]
            if v:
                data[k] = v
            else:
                data[k] = []
    return data


class SystemInfoCapture(DataCapture):

    def __init__(self, host=None, username=None, password=None, key_filename=None, log_queue=None, verbose=True, *args, **kwargs):
        """
        SystemInfoCapture is slightly different than most DataCapture classes. It will capture data at start
        but stop() doesn't do anything. We don't check differences between start and stop because it doesn't
        make sense to do so. What we really want to know is the hardware configuration during a test.

        :param host:
        :param username:
        :param password:
        :param key_filename:
        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.log_queue = log_queue
        logging.config.dictConfig(queued_logger_config(log_queue))
        self.logger = logging.getLogger('root')
        self.logger.info('Message in SystemInfoCapture')

        self.host = host
        self.username = username
        self.password = password
        self.key_filename = key_filename

        if key_filename is None and password is None:
            raise Exception('SystemInfo requires a password or SSH key file')

        self._data = {}
        self.si = None
        self.args = args
        self.kwargs = kwargs

    def setup(self):
        """
        Setup here is just initializing the SystemInfo instance
        :return:
        """
        self.logger.status('Running setup routine...')
        self.si = SystemInfo(self.host, self.username, self.password, self.key_filename, log_queue=self.log_queue,
                             *self.args, **self.kwargs)

    def teardown(self):
        """
        Nothing to do as we don't maintain any sort of connections or modify any systems
        :return:
        """
        self.logger.status('Passing on teardown')
        pass

    def start(self):
        self.logger.status('Collecting data at "start()"')
        self.si.get_all()
        self.data = self.si.system_info

    def stop(self):
        """
        Dummy function that doesn't actually do anything.
        :return:
        """
        self.logger.status('Passing on stop')
        pass

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value


if __name__ == "__main__":
    import pprint
    verbose = True
    auto_get = True
    key_filename = r'c:\Users\Administrator\Desktop\dev_sys_key.pem'
    auth = dict(host='192.168.1.15',username='root',key_filename=key_filename,password=None)
    si = SystemInfo(
        host='192.168.1.15',
        username='root',
        key_filename=key_filename,
        verbose=verbose,
        auto_get=auto_get)

    if auto_get:
        si.logger.result(si.system_info)

    #
    # sic = SystemInfoCapture(
    #     host='192.168.1.15',
    #     username='root',
    #     key_filename=key_filename,
    #     verbose=verbose,
    #     stream_log_level='info')
    #
    # sic.setup()
    # sic.start()
    # sic.logger.info('We started things')
    # sic.stop()
    # sic.teardown()
    # sic.logger.result(f'Data is: {sic.data}')
