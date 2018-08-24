## Importing events

* Create a superuser  (on a local instance, run `./manage.py createsuperuser`)
* Login as that user at /admin
* Create a Group (no permissions necessary)
* Edit current User and add to just created Group
* Create an Organization and assign the just created Group to it. The osdi source id has to be `moveon.org`.
* Create an Event Source with the noted osdi source id both as its osdi name and its event source name. Assign the created Organization as its Origin organization. Choose a crm type from the available choices (currently only actionkit_api is supported). Set update style to Manual only, and set Allows updates to no. Note the event source name for the next step.
* Run this command to import events from this source:
`./manage.py event_exim_update --source event_source_name`
* Newly imported events will be available for review at /admin/event_store/event/

## Finding and reviewing duplicate events

* Run this command to check imported events for duplicates:

`./manage.py event_dupe_finder`

* Potential duplicates will be available for review at /admin/event_exim/eventdupeguesses/
