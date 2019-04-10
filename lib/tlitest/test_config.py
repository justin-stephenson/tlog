""" tlog tests """

import os
import ast
import stat
import time
import socket
import inspect
import json
import pexpect
import pytest
import subprocess
from systemd import journal
from shutil import copyfile
from pexpect import pxssh
from tempfile import mkdtemp
from config import TlogRecSessionConfig
from test_tlog import *

TLITESTUSER = "tlitestlocaluser1"
TLITESTADMINUSER = "tlitestlocaladmin1"
TLOG_REC_SESSION_PROG = "/usr/bin/tlog-rec-session"
DEFAULT_TLOG_REC_SESSION_CONF = "/etc/tlog/tlog-rec-session.conf"

@pytest.fixture(scope="module")
def config_setup():
    conf_file = DEFAULT_TLOG_REC_SESSION_CONF
    backup_file = f"{conf_file}-orig"
    copyfile(conf_file, backup_file)
    yield config_setup
    # restore original configuration
    copyfile(backup_file, conf_file)
    os.remove(backup_file)

class TestTlogRecSession:
    """ tlog-rec-session tests """
    orig_hostname = socket.gethostname()
    tempdir = mkdtemp(prefix='/tmp/TestTlogRecSession.')
    user1 = TLITESTUSER
    admin1 = TLITESTADMINUSER
    os.chmod(tempdir, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO +
             stat.S_ISUID + stat.S_ISGID + stat.S_ISVTX)

    def check_configuration_output(self, program, pattern):
        cmd = [program, "--configuration"]
        proc = subprocess.run(cmd, capture_output=True) 
        assert pattern in str(proc.stdout)

    def test_rec_session_system_config_generic(self, config_setup):
        """
        Validate that tlog-rec-session observes generic
        settings in its system-wide configuration file
        """
        conf_file = DEFAULT_TLOG_REC_SESSION_CONF
        logfile = mklogfile(self.tempdir)
        input_notice = "TEST Notice Message"
        input_shell = "/bin/sh"

        config = TlogRecSessionConfig(shell=input_shell, notice=input_notice,
                                      writer="file", file_writer_path=logfile)
        config.generate_config(conf_file)

        pattern = '"writer":"file"'
        self.check_configuration_output(TLOG_REC_SESSION_PROG, pattern)

        msg = inspect.stack()[0][3]
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        shell.sendline(TLOG_REC_SESSION_PROG)
        shell.expect(input_notice)
        # make pexpect wait for tlog-rec-session to exec
        shell.sendline(f'echo {msg}')
        shell.expect(msg)
        shell.sendline('echo $SHELL')
        shell.expect(input_shell)
        shell.sendline('exit')
        os.chmod(logfile, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO +
                 stat.S_ISUID + stat.S_ISGID + stat.S_ISVTX)
        check_recording(shell, msg, logfile)
        shell.close

    def test_rec_session_system_config_file_writer(self, config_setup):
        """
        Validate that tlog-rec-session observes file writer
        settings in its system-wide configuration file
        """
        conf_file = DEFAULT_TLOG_REC_SESSION_CONF
        logfile = mklogfile(self.tempdir)

        config = TlogRecSessionConfig(writer='file', file_writer_path=logfile)
        config.generate_config(conf_file)

        pattern = '"writer":"file"'
        self.check_configuration_output(TLOG_REC_SESSION_PROG, pattern)

        msg = inspect.stack()[0][3]
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        shell.sendline(TLOG_REC_SESSION_PROG)
        # make pexpect wait for tlog-rec-session to exec
        shell.expect('ATTENTION')
        shell.sendline(f'echo {msg}')
        shell.expect(msg)
        shell.sendline('exit')
        os.chmod(logfile, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO +
                 stat.S_ISUID + stat.S_ISGID + stat.S_ISVTX)
        check_recording(shell, msg, logfile)
        shell.close

    def test_rec_session_system_config_journal_writer(self, config_setup):
        """
        Validate that tlog-rec-session observes journal writer
        settings in its system-wide configuration file
        """
        conf_file = DEFAULT_TLOG_REC_SESSION_CONF

        config = TlogRecSessionConfig(writer='journal')
        config.generate_config(conf_file)

        pattern = '"writer":"journal"'
        self.check_configuration_output(TLOG_REC_SESSION_PROG, pattern)

        msg = inspect.stack()[0][3]
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        shell.sendline(TLOG_REC_SESSION_PROG)
        # make pexpect wait for tlog-rec-session to exec
        shell.expect('ATTENTION')
        shell.sendline(f'echo {msg}')
        shell.expect(msg)
        shell.sendline('exit')
        check_recording(shell, msg)
        shell.close
