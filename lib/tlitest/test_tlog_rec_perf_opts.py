""" tlog tests """
import os
import stat
import json
from tempfile import mkdtemp

from misc import ssh_pexpect, \
                 mklogfile, check_recording, \
                 check_recording_missing, check_outfile

DEFAULT_PAYLOAD_SIZE = 2048


class TestTlogRecPerformanceOptions:
    """ Test performance related options for tlog-rec """
    user1 = 'tlitestlocaluser1'
    tempdir = mkdtemp(prefix='/tmp/TestTlogRec.')
    os.chmod(tempdir, stat.S_IRWXU + stat.S_IRWXG + stat.S_IRWXO +
             stat.S_ISUID + stat.S_ISGID + stat.S_ISVTX)

    def test_record_fast_input_with_latency(self):
        """
        Check tlog-rec caches data some time before logging
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--latency=9'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        check_recording(shell, 'test_199', logfile)
        shell.close()

    def test_record_fast_input_with_payload(self):
        """
        Check tlog-rec limits output payload size
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--payload=128'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        check_recording(shell, 'test_199', logfile)
        shell.close()

    def test_record_fast_input_with_limit_rate(self):
        """
        Check tlog-rec records session with limit-rate argument
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--limit-rate=10'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        shell.close()

    def test_record_fast_input_with_limit_burst(self):
        """
        Check tlog-rec allows limited burst of fast output
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--limit-rate=10 --limit-burst=100'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        shell.close()

    def test_record_fast_input_with_limit_action_drop(self):
        """
        Check tlog-rec drops output when logging limit reached
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--limit-rate=10 --limit-action=drop'
        cmd = 'cat /usr/share/dict/linux.words'
        shell.sendline('tlog-rec {} '
                       '-o {} {}'.format(opts, logfile, cmd))
        shell.close()
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        check_recording_missing(shell, 'Byronite', logfile)
        check_recording_missing(shell, 'zygote', logfile)

    def test_record_fast_input_with_limit_action_delay(self):
        """
        Check tlog-rec delays recording when logging limit reached
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--limit-rate=10 --limit-action=delay'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        check_outfile('test_199', logfile)
        shell.sendline('exit')
        check_recording(shell, 'test_199', logfile)
        shell.close()

    def test_record_fast_input_with_limit_action_pass(self):
        """
        Check tlog-rec ignores logging limits
        """
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = '--limit-rate=10 --limit-action=pass'
        shell.sendline('tlog-rec {} '
                       '-o {} /bin/bash'.format(opts, logfile))
        for num in range(0, 200):
            shell.sendline('echo test_{}'.format(num))
        shell.sendline('exit')
        check_recording(shell, 'test_199', logfile)
        shell.close()

    def test_record_payload_minimum(self):
        """
        Check tlog-rec segments log messages properly
        below payload size limit (minimum)
        """
        logfile = mklogfile(self.tempdir)
        payload_size = 32
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = f'--payload={payload_size}'
        shell.sendline('tlog-rec {} '
                       '-o {}'.format(opts, logfile))
        shell.set_unique_prompt()
        shell.sendline(f'cat /usr/share/doc/tlog/README.md')
        shell.expect('http://scribery.github.io/')
        shell.sendline('exit')
        with open(logfile) as tlog_recording_log:
            for line in tlog_recording_log:
                msg_dict = json.loads(line)
                assert len(msg_dict['out_txt']) < payload_size
        tlog_recording_log.close()
        shell.close()

    def test_record_payload_default(self):
        """
        Check tlog-rec segments log messages properly
        below payload size limit (default)
        """
        payload_size = DEFAULT_PAYLOAD_SIZE
        logfile = mklogfile(self.tempdir)
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        shell.sendline('tlog-rec -o {}'.format(logfile))
        shell.set_unique_prompt()
        shell.sendline(f'cat /usr/share/doc/tlog/README.md')
        shell.expect('http://scribery.github.io/')
        shell.sendline('exit')
        with open(logfile) as tlog_recording_log:
            for line in tlog_recording_log:
                msg_dict = json.loads(line)
                assert len(msg_dict['out_txt']) < payload_size
        tlog_recording_log.close()
        shell.close()

    def test_record_payload_large(self):
        """
        Check tlog-rec segments log messages properly
        below payload size limit (large)
        """
        logfile = mklogfile(self.tempdir)
        payload_size = 18342
        shell = ssh_pexpect(self.user1, 'Secret123', 'localhost')
        opts = f'--payload={payload_size}'
        shell.sendline('tlog-rec {} '
                       '-o {}'.format(opts, logfile))
        shell.set_unique_prompt()
        shell.sendline(f'cat /usr/share/doc/tlog/README.md')
        shell.expect('http://scribery.github.io/')
        shell.sendline('exit')
        with open(logfile) as tlog_recording_log:
            for line in tlog_recording_log:
                msg_dict = json.loads(line)
                assert len(msg_dict['out_txt']) < payload_size
        tlog_recording_log.close()
        shell.close()
