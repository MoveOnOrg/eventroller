import datetime
import re

from django.test import Client, TestCase, override_settings

"""
>>> response = c.post('/login/', {'username': 'john', 'password': 'smith'})
>>> response.status_code
>>> response = c.get('/customer/details/')
>>> response.content
b'<!DOCTYPE html...'

assertTrue
assertEqual
assertRedirects
assertContains
https://docs.djangoproject.com/en/1.9/topics/testing/tools/#assertions

"""
TESTSETTINGS = {
    'TESTING': True,
    'EVENT_PUBLIC_API': True,
    # add other custom settings here
}
@override_settings(**TESTSETTINGS)
class VolunteerTestCase(TestCase):

    #fixtures = ['baserecruit_fixtures']

    def setUp(self):
        self.c = Client()

    def test_volunteer_blankvisit(self):
        xxx = self.c.get('/foo/bar/')
        self.assertContains(xxx, 'yyy')
