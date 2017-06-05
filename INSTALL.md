## Development/Installation

## Deployment

There are two ways to change settings.  One is to set environment variables (documented below),
and the other is to create a ./local_settings.py file that will override settings in `eventroller/settings.py`

* `PRODUCTION`: set this as a variable to disable DEBUG=True
* `DB_HOSTNAME`, `DB_NAME`, `DB_USERNAME`, `DB_PASSWORD`, `DB_PORT` should all be set for db
* `REDISCACHE` should be in the form of `redis://127.0.0.1:6379/1` (or comma-separated list of servers). 
  The Redis cache is used for caching db-queries (with module `cachalot`) and also supporting
  the reviewer module (to review events) -- without this set, it uses a process instance of `fakeredis`
  which is fine for debugging but not for persisting data or sharing data across servers/processes at all.
* `EVENT_SOURCES`: This should be JSON structured data of information related to EventSource(s).
  It is a dictionary keyed off of the EventSource `name` value, and contains json data that overrides
  what would be in the `crm_data` for the corresponding `crm_type` (also a key)
  This enables the environment or a `local_settings.py` file to have the credentials for a system without
  storing them in a database for security purposes.
* `ALLOWED_HOSTS`: See the Django documentation for this setting -- this is *required* for non-DEBUG deployments
* `FORCE_SCRIPT_NAME`: See Django documentation (useful for setting a base path for the app that it's served from)
* `DJANGO_BASE_SECRET`: sets the Django settings.SECRET_KEY used for password hashing, etc.
* `LAMBDA_ZAPPA`: disables loading of local_settings.py files, which is useful for deploying with
  environment variables from a `zappa_settings.json` file to Amazon Lambda
