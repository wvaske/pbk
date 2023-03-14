#!/usr/bin/env python3

import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Perflosopher's benchmarking kit.")

    # Add a group for all of the standard options for a remote benchmark
    standard_parser = parser.add_argument_group(title='Standard options',
                                                description='Options for running a remote benchmark common to all '
                                                            'supported benchmarks')
    standard_parser.add_argument('--host', default='localhost')
    standard_parser.add_argument('--username')
    standard_parser.add_argument('--key-filename', help='File to use for SSH key authentication')

    datacapture_parser = parser.add_argument_group(title='Configuration for datacaptures during tests.')

    # Enable subparsers so each benchmark can have it's own options
    subparsers = parser.add_subparsers(title='Benchmarks',)
    add_openssl_parser_options(subparsers, [parser])
    add_fio_parser_options(subparsers, [parser])

    # Run the parser
    arguments = parser.parse_args()

    # Verify specific parameters can interact properly with each other
    if arguments.host != 'localhost' and arguments.username is None:
        parser.error(f'`--username` must be provided for non-localhost benchmarks')

    # Return the dictionary representation
    return vars(arguments)


def add_openssl_parser_options(subparsers, parents):
    # Set up the OpenSSL parser
    openssl_parser = subparsers.add_parser("openssl",
                                           parents=parents,
                                           help="Benchmark the performance of cryptographic algorithms with the "
                                                "`openssl -evp` command",
                                           add_help=False)
    openssl_parser.set_defaults(benchmark='openssl')

    openssl_group = openssl_parser.add_argument_group(title='openssl',
                                                      description='Options for cryptographic benchmarking')
    openssl_group.add_argument('--algorithm',
                               default='aes-128-cbc',
                               help="Commonly tested algorithms include: aes-128-cbc, aes-128-gcm, aes-256-cbc, "
                                    "aes-256-gcm. For the full list of supported algorithms please see the OpenSSL "
                                    "documentation")


def add_fio_parser_options(subparsers, parents):
    # Set up the FIO parser
    fio_parser = subparsers.add_parser("fio",
                                       parents=parents,
                                       help="Flexible I/O tester for doing block device performance testing",
                                       add_help=False)
    fio_parser.set_defaults(benchmark='fio')

    fio_group = fio_parser.add_argument_group(title='fio',
                                              description='Options for FIO benchmarking')
    fio_group.add_argument('--device', help="Device to benchmark")
    fio_group.add_argument('--blocksize', default='4k')
    fio_group.add_argument('--rwmixread', default=100)
    fio_group.add_argument('--numjobs', default=1)


def main():
    arguments = parse_arguments()
    print(arguments)


if __name__ == '__main__':
    main()
