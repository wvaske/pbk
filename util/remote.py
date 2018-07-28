import select
import paramiko


def send_ssh_command(command=None, host='127.0.0.1', username='root', password=None, key_filename=None,
                     logger=None, timeout=60):
    """
    The code comes from here: https://stackoverflow.com/questions/23504126/
    do-you-have-to-check-exit-status-ready-if-you-are-going-to-check-recv-ready
    """
    if hasattr(command, '__iter__') and not isinstance(command, str):
        command = [str(part) for part in command]
        command = ' '.join(command)

    conn = paramiko.SSHClient()
    conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if password is not None:
        conn.connect(host, username=username, password=password)
    elif key_filename is not None:
        pkey = paramiko.RSAKey.from_private_key_file(key_filename)
        conn.connect(host, username=username, pkey=pkey)
    else:
        raise SyntaxError(f'Need either password or ssh key file to send command')
    stdin, stdout, stderr = conn.exec_command(command)

    if logger: logger.info(f'Sent command: {command}')

    # get the shared channel for stdout/stderr/stdin
    channel = stdout.channel
    stdin.close()
    channel.shutdown_write()

    # read stdout/stderr in order to prevent read block hangs
    stdout_chunks = [stdout.channel.recv(len(stdout.channel.in_buffer))]
    stderr_chunks = []

    # chunked read to prevent stalls
    while not channel.closed or channel.recv_ready() or channel.recv_stderr_ready():
        # stop if channel was closed prematurely, and there is no data in the buffers.
        got_chunk = False
        readq, _, _ = select.select([stdout.channel], [], [], timeout)
        for c in readq:
            if c.recv_ready():
                stdout_chunks.append(stdout.channel.recv(len(c.in_buffer)))
                got_chunk = True
            if c.recv_stderr_ready():
                # make sure to read stderr to prevent stall
                stderr_chunks.append(stderr.channel.recv_stderr(len(c.in_stderr_buffer)))
                got_chunk = True
        '''
        1) make sure that there are at least 2 cycles with no data in the input buffers in 
             order to not exit too early (i.e. cat on a >200k file).
        2) if no data arrived in the last loop, check if we already received the exit code
        3) check if input buffers are empty
        4) exit the loop
        '''
        if not got_chunk \
                and stdout.channel.exit_status_ready() \
                and not stderr.channel.recv_stderr_ready() \
                and not stdout.channel.recv_ready():
            # indicate that we're not going to read from this channel anymore
            stdout.channel.shutdown_read()
            # close the channel
            stdout.channel.close()
            break  # exit as remote side is finished and our bufferes are empty

    # close all the pseudofiles
    stdout.close()
    stderr.close()

    ret_stdout = ''.join([chunk.decode() for chunk in stdout_chunks])
    ret_stderr = ''.join([chunk.decode() for chunk in stderr_chunks])

    return ret_stdout, ret_stderr


def linux_which(executable=None, host='127.0.0.1', username='root', password=None, key_filename=None,
                logger=None, timeout=60):

    cmd = f'which {executable}'
    stdout, stderr = send_ssh_command(cmd, host, username, password, key_filename, logger, timeout)

    if stdout is '':
        return None
    else:
        return stdout.strip()