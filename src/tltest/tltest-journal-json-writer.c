/*
 * Tlog tlog_journal_json_writer test.
 *
 * Copyright (C) 2015 Red Hat
 *
 * This file is part of tlog.
 *
 * Tlog is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by

 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with tlog; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */

#define _GNU_SOURCE

#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include <systemd/sd-journal.h>
#include <tlog/rc.h>
#include <tlog/json_writer.h>
#include <tlog/journal_json_writer.h>

#define MSG(_out_txt)                               \
        "{"                                         \
            "\"ver\":"      "\"2.2\","              \
            "\"host\":"     "\"localhost\","        \
            "\"rec\":"      "\"rec-1\","            \
            "\"user\":"     "\"user\","             \
            "\"term\":"     "\"xterm\","            \
            "\"session\":"  "1,"                    \
            "\"id\":"       "1,"                    \
            "\"pos\":"      "0,"                    \
            "\"timing\":"   "\"=0x0\","             \
            "\"in_txt\":"   "\"\","                 \
            "\"in_bin\":"   "[],"                   \
            "\"out_txt\":"  _out_txt                \
            "\"out_bin\":"  "[]"                    \
        "}\n"

struct tltest_journal_json_writer_input {
    bool test_priority; /* True for journal message priority tests */
    int priority;
    bool augment;
    const char *recording_id;
    const char *username;
    unsigned int session_id;
    size_t message_id;
    uint8_t *message;
};

static bool
find_journal_message(size_t message_id,
                     bool augment,
                     int priority,
                     bool test_priority)
{

    char *message_id_str = NULL;
    char *priority_str = NULL;
    sd_journal *j;
    int rc;
    bool found = false;

    rc = sd_journal_open(&j, SD_JOURNAL_LOCAL_ONLY);
    if (rc < 0) {
        goto done;
    }

    rc = asprintf(&message_id_str, "TLOG_ID=%zu", message_id);
    if (rc < 0) {
        fprintf(stderr, "Error printing message id\n");
        goto done;
    }

    rc = asprintf(&priority_str, "PRIORITY=%zu", priority);
    if (rc < 0) {
        fprintf(stderr, "Error printing priority\n");
        goto done;
    }

    SD_JOURNAL_FOREACH_BACKWARDS(j) {
        const char *d;
        size_t l;
        const char *str;

        if (augment == true) {
            /* Find TLOG_ID journal entry matching input */
            rc = sd_journal_get_data(j, "TLOG_ID", (const void**)&d, &l);
            if (rc >= 0) {
                if (strcmp(message_id_str, d) == 0) {
                    /* Not testing priority, succeed */
                    if (test_priority == false) {
                        found = true;
                        goto done;
                    /* Compare and match the message priority with the
                     * input priority */
                    } else if (test_priority == true) {
                        rc = sd_journal_get_data(j, "PRIORITY", (const void**)&d, &l);
                        if (strcmp(priority_str, d) == 0) {
                            found = true;
                            goto done;
                        }
                    }
                }
            }
        } else if (augment == false) {
            rc = sd_journal_get_data(j, "MESSAGE", (const void**)&d, &l);
            if (rc >= 0) {
                str = strstr(d, "augment_false_test_string");
                if (str != NULL) {
                    found = true;
                    goto done;
                }
            }
        }
    }

done:
    sd_journal_close(j);
    free(message_id_str);
    free(priority_str);

    return found;
}

static bool
tltest_journal_json_writer_run(const struct tltest_journal_json_writer_input *input)
{
    tlog_grc grc;
    struct tlog_json_writer *writer = NULL;
    uint8_t *message = (uint8_t *)input->message;

	size_t len;
    bool passed = false;

    grc = tlog_journal_json_writer_create(&writer, input->priority, input->augment,
                                          input->recording_id, input->username,
                                          input->session_id);
    if (grc != TLOG_RC_OK) {
        fprintf(stderr, "Failed creating writer: [%s]\n", tlog_grc_strerror(grc));
        passed = false;
        goto done;
    }

    passed = tlog_json_writer_is_valid(writer);
    if (passed == false) {
        fprintf(stderr, "Writer is invalid\n");
        passed = false;
        goto done;
    }

    len = strlen((const char *)message);
    grc = tlog_json_writer_write(writer,
                                 input->message_id,
                                 message,
                                 len);
    if (grc != TLOG_RC_OK) {
        fprintf(stderr, "Write failed: [%s]\n", tlog_grc_strerror(grc));
        passed = false;
        goto done;
    }

    passed = find_journal_message(input->message_id, input->augment,
                                  input->priority, input->test_priority);
    if (passed == false) {
        fprintf(stderr, "Error finding journal message\n");
        passed = false;
        goto done;
    }

done:
    tlog_json_writer_destroy(writer);

    return passed;
}

static bool
tltest_journal_json_writer(const char *test_name,
                           const struct tltest_journal_json_writer_input input)
{
    bool passed = false;

    passed = tltest_journal_json_writer_run(&input);

    fprintf(stderr, "%s: %s\n", (passed ? "PASS" : "FAIL"), test_name);

    return passed;
}

int
main(void)
{
    bool passed = false;
    int message_id = 1;

    passed = tltest_journal_json_writer("basic_write",
                                (struct tltest_journal_json_writer_input) {
                                    .test_priority = false,
                                    .priority = tlog_syslog_priority_from_str("info"),
                                    .augment = true,
                                    .recording_id = "rec-1",
                                    .session_id = 1,
                                    .username = "user",
                                    /* Increment message_id after each test to ensure
                                     * find_journal_message() does not match previously
                                     * written message */
                                    .message_id = message_id++,
                                    .message = (uint8_t *)MSG("ABCDEF")
                                });

    passed = tltest_journal_json_writer("augment_false",
                                (struct tltest_journal_json_writer_input) {
                                    .test_priority = false,
                                    .priority = tlog_syslog_priority_from_str("info"),
                                    .augment = false,
                                    .recording_id = "rec-1",
                                    .session_id = 1,
                                    .username = "user",
                                    .message_id = message_id++,
                                    .message = (uint8_t *)MSG("augment_false_test_string")
                                });

    passed = tltest_journal_json_writer("error_priority",
                                (struct tltest_journal_json_writer_input) {
                                    .test_priority = true,
                                    .priority = tlog_syslog_priority_from_str("error"),
                                    .augment = true,
                                    .recording_id = "rec-1",
                                    .session_id = 1,
                                    .username = "user",
                                    .message_id = message_id++,
                                    .message = (uint8_t *)MSG("Testing")
                                });

#ifndef NDEBUG
    passed = !tltest_journal_json_writer("invalid_input",
                                (struct tltest_journal_json_writer_input) {
                                    .test_priority = false,
                                    .priority = tlog_syslog_priority_from_str("info"),
                                    .augment = NULL,
                                    .recording_id = NULL,
                                    .session_id = 1,
                                    .username = NULL,
                                    .message_id = message_id++,
                                    .message = (uint8_t *)MSG("")
                                });
#endif

    return !passed;
}
