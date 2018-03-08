# EventRoller

For this project, the definition of an event is something that someone might RSVP to.
It definitely has a time, though may not have a place, if it's virtual.

## Apps

 * `event_store`: Basic event schema to accomodate different sources
 * `reviewer`: Admin interface and schemas to log reviews 
 * `event_exim`: Event exporter/importer -- traffic control and management for organziations

## Getting Started
### Installation
- Install python3, pip3 and virtualenv
- Run `virtualenv -p python3 venv` to set up your virtual environment
- Run `pip install -r requirements.txt` to get all the initial requirements
- Every time you start working on Eventroller run: `source venv/bin/activate` to boot up the virtual environment
- Install spatilite (similar to sqlite but with added location functionality)
    - ubuntu `apt-get install python-pyspatialite spatialite-bin`
    - macOSX `brew install libspatialite`


### Running the app
#### The first time
- Run `./manage.py migrate` to set up initial test database, auth, and admin interface.
- Then `./manage.py createsuperuser` to create admin user of the website

#### Every time
- Run the server with  `./manage.py runserver`
- Run the tests with `./manage.py test`

## Basic Workflow User Story (not yet implemented)

### As an organization that hosts events, with a CRM

* To start, we create a Group for our Organization and add staff members as Users
* In event_store we create an Organization record and connect it to the Group
* Then we go into event_exim and create an EventSource connecting to our CRM
* We are partners with Org2 -- so we create an Organization and EventSource for them as well
* We also want Org2's non-duplicate events to populate and sync back to our CRM, so 
  in event_exim we create an Org2OrgShare record, and mark our CRM's EventSource as allowing updates

#### Reviewing events

* Some events come from volunteers which need to be reviewed
* We mark our EventSource as allowing updates and go to the Event Reviewer view
  (which restricts by the organization(s) that I'm a group of.

#### Sharing events

* Org2 has its own public map and event store, and wants to share our events
* From our EventSource page, we can provide an API link that is public so they can pull in our events
* If Org2 wants to trust our instance, they can also put in EventSource credentials and mark them as
  allowing updates, along with an Org2OrgShare record and their CRM will be automatically synced.

