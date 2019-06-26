""" tlog tests """
import os
import ast
import stat
import time
import socket
from tempfile import mkdtemp

import pexpect
import pytest

import recording
import journal

from misc import check_recording, ssh_pexpect, mklogfile, \
                 check_outfile, check_journal, mkcfgfile, \
                 journal_find_last

TLOG_TEST_USER = "tlitestlocaluser1"

class TestTlogRec:
    """ tlog-rec tests """
    testuser = TLOG_TEST_USER
    orig_hostname = socket.gethostname()
    tempdir = mkdtemp(prefix='/tmp/TestTlogRec.')
    user1 = 'tlitestlocaluser1'
    admin1 = 'tlitestlocaladmin1'
    os.chmod(tempdir, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO +
             stat.S_ISUID + stat.S_ISGID + stat.S_ISVTX)

    @pytest.mark.tier1
    def test_record_command_to_file(self):
        """
        Check tlog-rec preserves output when reording to file
        """
        writer_type = "file"
        command = "uname"
        expected_cmd_output = "Linux"

        logfile = mklogfile(self.tempdir)
        recording.record_simple_command(writer_type, command, logfile)
        recording.validate_command_logfile(f'out_txt\":\"{expected_cmd_output}', logfile)
        recording.validate_command_playback(expected_cmd_output, logfile)

    @pytest.mark.tier1
    def test_record_command_to_journal(self):
        """
        Check tlog-rec preserves output when recording to journal
        """
        writer_type = "journal"
        test_string = 'test_record_to_journal'
        command = f'echo {test_string}'

        recording.record_simple_command(writer_type, command)
        recording.validate_command_journal(test_string)
        recording.validate_command_playback(test_string)

    @pytest.mark.tier1
    def test_record_command_to_syslog(self):
        """
        Check tlog-rec preserves output when recording to syslog
        """
        writer_type = "syslog"
        test_string = 'test_record_to_syslog'
        command = f'echo {test_string}'

        recording.record_simple_command(writer_type, command)
        recording.validate_command_journal(test_string)

    def test_record_interactive_session(self):
        """
        Check tlog-rec preserves activity during interactive
        session in recordings
        """
        logfile = mklogfile(self.tempdir)
        writer_type = "file"
        test_string = "test_interactive"

        shell = recording.record_interactive_command(writer_type, logfile)
        shell.sendline('uname')
        shell.expect('Linux')
        shell.sendline(f'echo {test_string}')
        shell.expect(test_string)
        shell.sendline('exit')

        recording.validate_command_logfile(test_string, logfile)
        recording.validate_command_playback(test_string, logfile)

    def test_record_binary_output(self):
        """
        Check tlog-rec preserves binary output in recordings
        """
        writer_type = "file"
        command = "cat /usr/bin/gzip"
        expected_cmd_output = '\\u0000'

        logfile = mklogfile(self.tempdir)
        recording.record_simple_command(writer_type, command, logfile)
        recording.validate_command_logfile(expected_cmd_output, logfile)
        recording.validate_command_playback('\u0000', logfile)


    def test_record_diff_char_sets(self):
        """
        Check tlog-rec preserves non-English I/O in recordings
        """
        writer_type = "file"
        encoding = 'utf-8'

        test_string = 'найдена'
        logfile = '{}-ru_RU'.format(mklogfile(self.tempdir))
        shell = recording.record_interactive_command(writer_type, logfile)
        shell.sendline('export LANG=ru_RU.utf8')
        shell.sendline('badcommand')
        shell.sendline('exit')

        recording.validate_command_logfile(test_string, logfile)
        recording.validate_command_playback(test_string, logfile,
                encoding)

        test_string = 'βρέθηκε'
        logfile = '{}-el_GR'.format(mklogfile(self.tempdir))
        shell = recording.record_interactive_command(writer_type, logfile)
        shell.sendline('export LANG=el_GR.utf8')
        shell.sendline('badcommand')
        shell.sendline('exit')

        recording.validate_command_logfile(test_string, logfile)
        recording.validate_command_playback(test_string, logfile,
                encoding)

        test_string = 'Watérmân'
        logfile = '{}-en_US'.format(mklogfile(self.tempdir))
        shell = recording.record_interactive_command(writer_type, logfile)
        shell.sendline('export LANG=en_US.utf8')
        shell.sendline('echo Watérmân')
        shell.sendline('exit')

        recording.validate_command_logfile(test_string, logfile)
        recording.validate_command_playback(test_string, logfile,
                encoding)

    def test_record_fast_input(self):
        """
        Check tlog-rec preserves fast flooded I/O in recordings
        """
        writer_type = "file"

        logfile = mklogfile(self.tempdir)
        shell = recording.record_interactive_command(writer_type, logfile)
        for num in range(0, 2000):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        for num in range(0, 2000, 100):
            recording.validate_command_logfile(test_string, logfile)

    def test_record_as_unprivileged_user(self):
        """
        Check tlog-rec preserves unauthorized activity of
        unprivileged user in recordings
        """
        writer_type = "file"
        test_string = 'test1123out'

        logfile = mklogfile(self.tempdir)
        shell = recording.record_interactive_command(writer_type, logfile)
        shell.sendline('whoami')
        shell.expect(self.user1)
        shell.sendline('echo test1123out')
        shell.sendline('sleep 2')
        shell.sendline('ls -ltr /var/log/audit')
        shell.sendline('exit')
        recording.validate_command_logfile(test_string, logfile)
        recording.validate_command_playback(test_string, logfile)
        recording.validate_command_logfile('Permission denied', logfile)
        recording.validate_command_playback('Permission denied', logfile)

    @pytest.mark.root_required
    def test_record_as_admin_user(self):
        """
        Check tlog-rec preserves sudo activity of admin user in
        recordings
        """
        logfile = mklogfile(self.tempdir)
        cfg = '''
        %wheel        ALL=(ALL)       NOPASSWD: ALL
        '''
        mkcfgfile('/etc/sudoers.d/01_wheel_nopass', cfg)
        shell = ssh_pexpect(self.admin1, 'Secret123', 'localhost')
        shell.sendline('tlog-rec -o {}'.format(logfile))
        shell.sendline('whoami')
        shell.expect(self.admin1)
        shell.sendline('sleep 2')
        shell.sendline('echo test1223')
        shell.expect('test1223')
        shell.sendline('sudo ls -ltr /var/log/audit')
        shell.expect('audit.log')
        shell.sendline('exit')
        check_outfile('test1223', logfile)
        check_recording(shell, 'test1223', logfile)
        shell.close()
        shell = ssh_pexpect(self.admin1, 'Secret123', 'localhost')
        check_recording(shell, 'audit.log', logfile)
        shell.close()

    @pytest.mark.root_required
    def test_record_from_different_hostnames(self):
        """
        Check tlog-rec reflects hostname changes in recordings

        This is to simulate receiving remote journal sessions
        """
        oldname = socket.gethostname()
        shell = pexpect.spawn('/bin/bash')
        for num in range(0, 3):
            newname = 'test{}-{}'.format(num, oldname)
            socket.sethostname(newname)
            open('/etc/hostname', 'w').write(newname)
            shell.sendline('hostname')
            shell.expect(newname)
            time.sleep(1)
            shell.sendline('tlog-rec -w journal whoami')
            time.sleep(1)
            shell.sendline('hostnamectl status')
            time.sleep(1)
            entry = journal_find_last()
            message = entry['MESSAGE']
            mhostname = ast.literal_eval(message)['host']
            assert mhostname == newname
            time.sleep(1)
        socket.sethostname(oldname)
        open('/etc/hostname', 'w').write(oldname)

    @classmethod
    def teardown_class(cls):
        """ teardown for TestTlogRec """
