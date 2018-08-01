#!/usr/bin/env python3.6

import sys
import functools
import multiprocessing

from pbk.util.mp import SystemConnectionProcess
from pbk.util.remote import send_ssh_command, linux_which
from pbk.util.perflogger import LoggedObject, get_queued_logger
from pbk.util.data_capture import DataCapture


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

        self.logger.verboser(f'System info prerequisites: {self.prerequisites}')
        for prereq in self.prerequisites:
            if linux_which(prereq, host, username, password, key_filename) is None:
                self.logger.warning(f'Prerequisite "{prereq}" is not met')

        if auto_get:
            self.get_all()

    def get_all(self):
        self.logger.status(f'Getting System Info data from all configured sources on host {self.auth["host"]}')
        process_pool = []
        data_queue = multiprocessing.Queue()
        for cls in self.get_classes:
            process_pool.append(cls(data_queue, **self.auth, log_queue=self.log_queue))

        for p in process_pool:
            p.daemon = True
            p.start()
            self.logger.verboser(f'Started SysInfo getter process: {p.name}')

        self.logger.verboser('Joining SysInfo getter processes')
        [p.join() for p in process_pool]
        for i in range(len(self.get_classes)):
            self.system_info.update(data_queue.get())

        self.logger.verbose('Getting all SysInfo is complete')


class SystemInfoCapture(DataCapture):

    def __init__(self, host=None, username=None, password=None, key_filename=None, *args, **kwargs):
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
        self.host = host
        self.username = username
        self.password = password
        self.key_filename = key_filename

        if key_filename is None and password is None:
            raise Exception('SystemInfo requires a password or SSH key file')

        self.si = None
        self.args = args
        self.kwargs = kwargs

    def setup(self):
        """
        Setup here is just initializing the SystemInfo instance
        :return:
        """
        self.si = SystemInfo(self.host, self.username, self.password, self.key_filename, *self.args, **self.kwargs)
        self.logger.debug(f'Made instance of SI with args: {self.args} and kwargs: {self.kwargs}')

    def start(self):
        self.si.get_all()
        self.data = self.si.system_info



class GetInfo(SystemConnectionProcess):

    def __init__(self, result_queue=None, *args, **kwargs):
        self.required_kwargs = [result_queue]
        super().__init__(*args, **kwargs)
        self.result_queue = result_queue


class GetDmidecode(GetInfo):

    prerequisites = ['dmidecode']

    def run(self):
        self.logger = get_queued_logger(self.log_queue)
        stdout, stderr = self.send_command('dmidecode')
        self.logger.verboser(f'stdout length: {len(stdout)}')
        self.logger.debug(f'Parsing dmidecode stdout:\n {stdout}')
        if stdout is "":
            self.logger.error('Did not get data for dmidecode command')
            ret_data = None
        else:
            self.logger.verboser('Beginning parse of dmidecode')
            self.logger.debug(f'Repr of stdout: {repr(stdout)}')
            ret_data = parse_dmidecode_output(stdout)
            self.logger.verbose(f'dmidecode returned {len(ret_data.keys())} sections')

        self.result_queue.put({'dmidecode': ret_data})
        return ret_data


class GetModinfo(GetInfo):

    prerequisites = ['modprobe', 'modinfo']

    def run(self):
        ret_data = None
        self.result_queue.put({'modinfo': ret_data})
        return ret_data


class GetLspci(GetInfo):

    prerequisites = ['lspci']

    def run(self):
        ret_data = None
        self.result_queue.put({'lspci': ret_data})
        return ret_data


class GetUname(GetInfo):

    prerequisites = ['uname']

    def run(self):
        """
        Uname supports a set of flags to return specific information:
            -s, --kernel - name        print the kernel name
            - n, --nodename           print the network node hostname
            - r, --kernel - release     print the kernel release
            - v, --kernel - version     print the kernel version
            - m, --machine            print the machine hardware name
            - p, --processor          print the processor type(non - portable)
            - i, --hardware - platform  print the hardware platform(non - portable)
            - o, --operating - system   print the operating system
        :return:
        """
        uname_flags = dict(s='kernel', n='nodename', r='kernel-release', v='kernel-version',
                           m='machine', p='processor', i='hardware-platform', o='operating-system')
        uname_result = {}

        for flag, name in uname_flags.items():
            stdout, _ = self.send_command(f'uname -{flag}')
            uname_result[name] = stdout.strip()

        self.result_queue.put({'uname': uname_result})
        return uname_result


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
