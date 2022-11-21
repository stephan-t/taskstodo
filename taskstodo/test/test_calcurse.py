#!/usr/bin/env python3

import unittest
import os
import sys
import hashlib

from .. import tasklists
from .. import tasks
from .. import calcurse

from io import StringIO
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

DATA_DIR = os.path.join(os.getcwd(), 'caldurse')


class TestSyncFunctions(unittest.TestCase):
    """Test calcurse sync functions."""

    def authUser(self):
        """Setup credentials to access API."""

        SCOPES = ['https://www.googleapis.com/auth/tasks']

        self.creds = None
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json',
                                                               SCOPES)
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

    def setUp(self):
        """Setup test environment."""
        self.authUser()
        self.list_title = 'test list'
        tasklists.create_tasklist(self.creds, self.list_title, False)

        # Create Google tasks
        tasks.create_task(self.creds, self.list_title, 'test task 0',
                          'test note', -1, False)

        # Create calcurse tasks file and tasks
        with open(os.path.join(DATA_DIR, 'todo'), 'w') as f:
            f.write('[0] test task 1\n[0] test task 2\n')

            notes_dir = os.path.join(DATA_DIR, 'notes')
            try:
                os.mkdir(notes_dir)
            except FileExistsError:
                pass

            # Create calcurse task note
            note_bytes = bytes('test note', 'utf-8')
            note_hash = hashlib.sha1(note_bytes).hexdigest()
            f.write(f"[0]>{note_hash} test task 3\n")

            with open(os.path.join(notes_dir, note_hash), 'w') as f:
                f.write('test note\n')

        # Capture stdout to check correctness of output
        self.output = StringIO()
        sys.stdout = self.output

    def test_get_calcurse_tasks(self):
        """Get tasks from calcurse."""
        calcurse_tasks = calcurse.get_calcurse_tasks(DATA_DIR)
        calcurse_task = {'title': 'test task 1'}
        self.assertIn(calcurse_task, calcurse_tasks)
        self.assertEqual('test note', calcurse_tasks[2]['note'])

    def test_add_calcurse_tasks(self):
        """Add tasks to calcurse."""
        task_note = 'test note'
        new_task = [{'title': 'test task 4', 'note': task_note}]
        calcurse.add_calcurse_tasks(new_task, DATA_DIR)

        calcurse_tasks = calcurse.get_calcurse_tasks(DATA_DIR)
        self.assertIn(new_task[0], calcurse_tasks)
        self.assertEqual(task_note, calcurse_tasks[3]['note'])

    def test_get_google_tasks(self):
        """Get tasks from Google."""
        google_tasks = calcurse.get_google_tasks(self.creds, self.list_title,
                                                 -1)
        google_task = {'title': 'test task 0', 'note': 'test note'}
        self.assertIn(google_task, google_tasks)

    def test_add_google_tasks(self):
        """Add tasks to Google."""

        new_task_1 = {'title': 'test task 5'}
        new_task_2 = {'title': 'test task 6', 'note': 'test note'}
        new_tasks = [new_task_1, new_task_2]

        calcurse.add_google_tasks(self.creds, self.list_title, -1, new_tasks)
        self.assertIn(new_task_1, new_tasks)
        self.assertIn(new_task_2, new_tasks)

    def tearDown(self):
        """Cleanup test environment."""
        self.output.truncate(0)

        tasklists.print_all_tasklists(self.creds, 100, False)
        num_lists = self.output.getvalue().splitlines().count(
                f'- {self.list_title}')

        self.output.close()

        for _ in range(num_lists):
            tasklists.delete_tasklist(self.creds, self.list_title, 0, False)


if __name__ == '__main__':
    unittest.main()
