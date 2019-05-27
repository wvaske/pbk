
import ipaddress

from pbk.util.remote import send_ssh_command
from pbk.util.descriptors import ValueChecked
from pbk.execution import TestExecutor


class OpenSSLTest(TestExecutor):

    ALGORITHMS = ['md2', 'md4', 'md5', 'hmac', 'sha1', 'sha256', 'sha512', 'whirlpoolrmd160', 'idea-cbc', 'seed-cbc',
                  'rc2-cbc', 'rc5-cbc', 'bf-cbc', 'des-cbc', 'des-ede3', 'aes-128-cbc', 'aes-192-cbc', 'aes-256-cbc',
                  'aes-128-ige', 'aes-192-ige', 'aes-256-ige', 'camellia-128-cbc', 'camellia-192-cbc',
                  'camellia-256-cbc', 'rc4', 'rsa512', 'rsa1024', 'rsa2048', 'rsa4096', 'dsa512', 'dsa1024', 'dsa2048',
                  'ecdsap256', 'ecdsap384', 'ecdsap521', 'ecdsa', 'ecdhp256', 'ecdhp384', 'ecdhp521', 'ecdh', 'idea',
                  'seed', 'rc2', 'des', 'aes', 'camellia', 'rsa', 'blowfish']

    algorithm = ValueChecked(allowed_values=ALGORITHMS, prop_name='algorithm', allow_none=False)

    def __init__(self, host=None, username=None, password=None, engine=None, algorithm=None, parallel=1, decrypt=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.username = username
        self.password = password
        self.engine = engine
        self.algorithm = algorithm
        self.parallel = parallel
        self.decrypt = decrypt

        required_params = [host, username, password, algorithm]
        for param in required_params:
            if param is None:
                raise ValueError(f'Parameter {param.__name__} needs a non-None value')

    def __str__(self):
        return str(dict(host=self.host, engine=self.engine, algorithm=self.algorithm, parallel=self.parallel,
                        decrypt=self.decrypt))

    def setup(self):
        self.logger.status(f'Starting setup for test: {self}')

    def execute(self):
        self.logger.status(f'Starting execution of test: {self}')
        cmd = ['openssl', 'speed', '-evp', self.algorithm, '-elapsed', '-mr']
        if self.decrypt:
            cmd += '-decrypt'

        self.logger.debug(f'Sending command: {cmd} with: {self.host} {self.username} {self.password}')
        stdout, stderr = send_ssh_command(self.host, self.username, self.password, cmd)

        result = self._parse_mr_stdout(stdout)
        self.logger.result(f'{result}')

    def teardown(self):
        self.logger.status(f'Doing teardown for test: {self}')

    @staticmethod
    def _parse_mr_stdout(stdout):
        block_sizes, kbytes_per_sec = stdout.split()
        block_sizes = block_sizes.split(':')[1:]
        kbytes_per_sec = kbytes_per_sec.split(':')[3:]

        return dict(zip(block_sizes, kbytes_per_sec))
