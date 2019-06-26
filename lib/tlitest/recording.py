""" tlog integration tests recording module """

import sys
import time
import ast

import pexpect

import journal

TLOG_REC_PROG = "/usr/bin/tlog-rec"
TLOG_REC_DEFAULT_SHELL = "/bin/bash"

def record_simple_command(writer, command, logfile=None):
    """
    Run command under the tlog-rec recording program, waiting
    for the command to complete. A valid tlog-rec writer type
    string must be provided by the caller.
    """
    tlog_rec_prog = TLOG_REC_PROG

    if writer == "journal" or writer == "syslog":
        command = f'{tlog_rec_prog} -w {writer} {command}'
    else:
        command = f'{tlog_rec_prog} -w {writer} -o {logfile} {command}'

    if __debug__:
        print(f'DEBUG: executing {command}')
    output = pexpect.run(command)

def record_interactive_command(writer, logfile):
    """
    Start an interactive shell with tlog-rec under pexpect, allowing
    interaction with the pexpect spawn class.

    Returns the child pexpect spawn instance to interact with.
    """
    tlog_rec_prog = TLOG_REC_PROG
    command = f'{tlog_rec_prog} -w {writer} -o {logfile} /bin/bash'

    if __debug__:
        print(f'DEBUG: spawning {command}')
    child = pexpect.spawn(command, echo=False)

    # Disable canonical input processing
    child.sendline('stty -icanon')

    time.sleep(3)

    return child

def validate_command_logfile(pattern, logfile):
    """
    Open and read the contents of logfile, checking that pattern
    exists as a substring.

    Intended for validating program or script output, previously
    recorded with the tlog file writer.

    """
    time.sleep(1)
    for _ in range(0, 10):
        file1 = open(logfile, 'r')
        content = file1.read()
        file1.close()
        if pattern in content:
            break
        else:
            time.sleep(5)
    assert pattern in content

def validate_command_journal(pattern):
    """
    Check that pattern matches the output text('out_txt' of MESSAGE field)
    of the most recently logged tlog journal entry.

    Intended for validating program or script output, previously
    recorded with the tlog journal writer.
    """
    time.sleep(1)
    for _ in range(0, 10):
        entry = journal.journal_find_last()
        message = entry['MESSAGE']
        out_txt = ast.literal_eval(message)['out_txt']
        if pattern in out_txt:
            break
        else:
            time.sleep(5)
    assert pattern in out_txt

def validate_command_playback(pattern, filename=None, encoding=None):
    """
    Playback a recording and validate the playback output matches a
    specified string pattern.

    Intended for validating a previous recording.
    """
    shell = pexpect.spawn('/bin/bash', encoding=encoding)
    time.sleep(1)
    if filename is not None:
        cmd = 'tlog-play -i {}'.format(filename)
    else:
        entry = journal.journal_find_last()
        message = entry['MESSAGE']
        rec = ast.literal_eval(message)['rec']
        tlog_rec = 'TLOG_REC={}'.format(rec)
        cmd = 'tlog-play -r journal -M {}'.format(tlog_rec)
    shell2 = pexpect.spawn(cmd, encoding=encoding)
    out = shell2.expect([pexpect.TIMEOUT, pattern], timeout=10)
    if out == 0:
        print('\ncheck_recording TIMEOUT')
    assert out == 1
