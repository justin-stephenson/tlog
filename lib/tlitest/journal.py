""" tlog integration tests journal module """

import time
import ast
import systemd

def journal_find_last():
    """ Find the last TLOG_REC journal entry """
    j = systemd.journal.Reader()
    j.seek_tail()
    while True:
        entry = j.get_previous()

        if '_COMM' in entry:
            matchfield = '_COMM'
        elif 'SYSLOG_IDENTIFIER' in entry:
            matchfield = 'SYSLOG_IDENTIFIER'
        else:
            continue

        if 'tlog' in entry[matchfield]:
            return entry
        elif not entry:
            raise ValueError('Did not find TLOG_REC entry in journal')
