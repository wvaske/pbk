
import functools

from pbk.util.remote import send_ssh_command, linux_which
from pbk.util.perflogger import LoggedObject
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
        self.send_command = functools.partial(
            send_ssh_command, host=host, username=username, password=password, key_filename=key_filename)

        self.prerequisites = []
        if auto_get is True:
            self.logger.status(f'Getting data from all possible sources on host {host}')

        self.get_methods = [i for i in dir(self)
                            if i.startswith('get_')
                            and 'method' in str(type(getattr(self, i)))
                            and i != 'get_all']
        self.logger.info(f'Available system info sources: {[meth.lstrip("get_") for meth in self.get_methods]}')

        for meth in self.get_methods:
            self.prerequisites.extend(getattr(self, meth)(get_prerequisites=True))

        self.logger.info(f'System info prerequisites: {self.prerequisites}')
        for prereq in self.prerequisites:
            if linux_which(prereq, host, username, password, key_filename) is None:
                self.logger.warning(f'Prerequisite "{prereq}" is not met')

        if auto_get:
            self.get_all()

    def get_all(self):
        for meth in self.get_methods:
            getattr(self, meth)()
            getter_name = meth.lstrip("get_")
            if self.system_info.get(getter_name):
                self.logger.status(f'Fetched data from {getter_name}.')
            else:
                self.logger.warning(f'Did not get data from {getter_name}')

        return self.system_info

    def get_dmidecode(self, get_prerequisites=False):
        if get_prerequisites:
            return

        stdout, stderr = self.send_command('dmidecode')
        self.logger.verbose(f'stdout length: {len(stdout)}')
        self.logger.verboser(f'Parsing dmidecode stdout:\n {stdout}')
        if stdout is "":
            self.logger.error('Did not get data for dmidecode command')
            self.system_info['dmidecode'] = None
            return None
        else:
            self.logger.verbose('Beginning parse of dmidecode')
            self.logger.verboser(f'Repr of stdout: {repr(stdout)}')
            parsed_dmi = parse_dmidecode_output(stdout)
            self.system_info['dmidecode'] = parsed_dmi
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

        self._data = {}
        self.si = None

    def setup(self):
        """
        Setup here is just initializing the SystemInfo instance
        :return:
        """
        self.logger.status('Running setup routine...')
        self.si = SystemInfo(self.host, self.username, self.password, self.key_filename, logger=self.logger)

    def teardown(self):
        """
        Nothing to do as we don't maintain any sort of connections or modify any systems
        :return:
        """
        self.logger.status('Passing on teardown')
        pass

    def start(self):
        self.logger.status('Collecting data at "start()"')
        self.data = self.si.get_all()

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
    # si = SystemInfo(
    #     host='192.168.1.15',
    #     username='root',
    #     key_filename=key_filename,
    #     verbose=verbose,
    #     auto_get=auto_get)
    #
    # if auto_get:
    #     si.logger.result(pprint.pformat(si.system_info))

    sic = SystemInfoCapture(
        host='192.168.1.15',
        username='root',
        key_filename=key_filename,
        verbose=verbose,
        stream_log_level='info')

    sic.setup()
    sic.start()
    sic.logger.info('We started things')
    sic.stop()
    sic.teardown()
    sic.logger.result(f'Data is: {sic.data}')
