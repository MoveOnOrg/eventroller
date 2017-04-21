=EventRoller

For this project, the definition of an event is something that someone might RSVP to.
It definitely has a time, though may not have a place, if it's virtual.

== Apps

 * `event_store`: Basic event schema to accomodate different sources
 * `reviewer`: Admin interface and schemas to log reviews 
 * `event_exim`: Event exporter/importer -- traffic control and management for organziations


== Basic Workflow User Story (not yet implemented)

=== As an organization that hosts events, with a CRM

* To start, we create a Group for our Organization and add staff members as Users
* In event_store we create an Organization record and connect it to the Group
* Then we go into event_exim and create an EventSource connecting to our CRM
* We are partners with Org2 -- so we create an Organization and EventSource for them as well
* We also want Org2's non-duplicate events to populate and sync back to our CRM, so 
  in event_exim we create an Org2OrgShare record, and mark our CRM's EventSource as allowing updates

==== Reviewing events

* Some events come from volunteers which need to be reviewed
* We mark our EventSource as allowing updates and go to the Event Reviewer view
  (which restricts by the organization(s) that I'm a group of.

==== Sharing events

* Org2 has its own public map and event store, and wants to share our events
* From our EventSource page, we can provide an API link that is public so they can pull in our events
* If Org2 wants to trust our instance, they can also put in EventSource credentials and mark them as
  allowing updates, along with an Org2OrgShare record and their CRM will be automatically synced.

