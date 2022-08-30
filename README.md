# About #

Pycroft is the current user management system of the AG DSN student
network.  It is based on [Flask](http://flask.pocoo.org) and expects a
[Postgres](https://www.postgresql.org/) database making use of the
[SQLAlchemy ORM](http://www.sqlalchemy.org/).

# Cloning this directory #

A basic understanding of [git](https://git-scm.com/) is advisable.
The first step should be to clone this repository via `git clone --recursive
<url>`, using what clone url shows you above
[this very readme](https://github.com/agdsn/pycroft).

# Setup #

An easy way of doing the setup is by using docker-compose.

## Installing Docker and docker-compose ##

Follow the
guides [here](https://www.docker.com/community-edition#download)
and [here](https://docs.docker.com/compose/install/).
You will need at least docker engine `17.06.0+` and a docker compose `1.16.0+`.

Also, note that you might have to add your user to the `docker` group
for running docker as a non-root:

```
sudo usermod -aG docker $(whoami)
```

After adding yourself to a new group, you need to obtain a new session,
by e.g. logging out and in again.

You should now be able to run `docker-compose config` and see the
current configuration.

## Defining `UID` and `GID`

To set the `UID` and `GID` build arguments of the `agdsn/pycroft-base` image
with `docker-compose`, use an `docker-compose` `.env` file:

```dotenv
UID=<your-uid>
GID=<your-gid>
```

An `.env` template is included as `example.env` in the project root.
Copy the example to `.env` and set the correct values for your user,
`docker-compose` will automatically pick up the contents of this file.
The example also includes other useful environment variables, such as
`COMPOSE_PROJECT_NAME`.

You can also use environment variables from your shell to specify the UID/GID
build arguments when invoking `docker-compose`.
The docker-compose files pass the `UID` and `GID` environment variables as build
arguments to docker.
Don't be fooled by your shell however by executing the following command and
feeling safe, if it outputs your UID:

```bash
echo $UID
```

Bash and zsh automatically define this variable, but do not export it:

```bash
python3 -c 'import os; print(os.getenv("UID"))'
```

You have to explicitly export the variable:

```bash
export UID
# Bash does not set GID, zsh does, so you can omit the assignment with zsh:
export GID=$(id -g)
```

You should put these lines somewhere in your shell's startup script (e.g.
`.profile` in your `$HOME`), so that it is always defined, if you want to rely on these
variables instead of an `.env` file.

You could also the `--build-arg` option of `docker-compose build`,
but this is not advised as it can easily be forgotten.

## Other variables

### `COMPOSE_PROJECT_NAME`

`docker-compose` uses the name of the directory, the compose file resides in, as
the *project name*.
This name is used as a prefix for all objects (containers, volumes, networks)
created by `docker-compose` by default.

To use a different project name, use the `COMPOSE_PROJECT_NAME` environment
variable.

### `TAG`
The tag of the images created by `docker-compose` can be specified with the
`TAG` environment variable, which defaults to `latest`, e.g.:

```bash
TAG=1.2.3 docker-compose -f docker-compose.prod.yml build
```

This will tag all generated images with the tag `1.2.3`.

## Starting an environment

A complete environment can be started by running

```bash
docker-compose up -d
```

This will start all *dev* environment.
`docker-compose` will build necessary images if not already present,
it will *not* however automatically rebuild the images if the `Dockerfile`s or
any files used by them are modified.

If you run this command for the first time,
this might take a while, as a series of packages and image are downloaded,
so grab a cup of tea and relax.

All services, except `base`, which is only used to build the
`agdsn/pycroft-base` image, should now be marked as `UP`, if you take a look at
`docker-compose ps`.
There you see which port forwardings have been set up (remember the port `web` has been exposed!)

Because you started them in detached mode, you will not see what they
print to stdout.
You can inspect the output like this:

```sh
docker-compose logs # for all services
docker-compose logs dev-app  # for one service
docker-compose logs -f --tail=50 dev-app  # Print the last 50 entries and follow the logs
```

The last command should tell you that the server spawned an instance
at 0.0.0.0:5000 from inside the container.

**But don't be too excited, pycroft will fail after the login – we
have to set up the database.**

To start another enviroment, run `docker-compose` with the`-f` flag to specify a
different compose file, e.g.:

```bash
docker-compose -f docker-compose.test.yml up -d
```

This would start the **test** environment.

## (Re-)building/Pulling images

You can (re-)build/pull a particular service/image (or all of them if no service
is specified) by running:

```bash
docker-compose build --force-rm --pull [service]
```

## PyCharm Integration

In order to integrate the setup into PyCharm,
make sure that you are using the Professional edition, because the Docker
integration feature is only available in the Professional edition of PyCharm.
Also make sure that you have updated to a recent version,
there were important bug fixes with regards to the Docker integration.

### Project interpreters

The **dev** and **test** environments should be added to PyCharm as project
interpreters.

Go to “Settings” → “Project: Pycroft” → “Project Interpreter” → Gear icon
→ “Add remote” → “Docker Compose”.

Create a new server for your local machine (use the default settings for that),
if none exists yet.
Select the config file `docker-compose.dev.yml` in the project root,
select the the service: `dev-app`,
and type in the following path for the python interpreter:
`/opt/pycroft/venv/bin/python`.

Repeat the same thing for **test** environment defined in
`docker-compose.test.yml`.

Save, and make sure the correct interpreter (**dev**, not
**test**) is selected as default for the project (“Project settings” →
“Project interpreter”).
As a proof of concept, you can run a “Python Console” inside PyCharm.

### Run Configurations

A few run configurations are already included in the project's `.idea` folder.
If you have created the project interpreters according to the above steps,
the appropriate interpreters should have been autoselected for each run configuration.

### Database connections (optional)

You can access databases with PyCharm if you are so inclined.
First, you need to obtain the IP address of the database container.
If you didn't change the project name, the following command will
yield the IP address of the database development container:

```bash
docker inspect pycroft_dev-db_1 -f '{{ .NetworkSettings.Networks.pycroft_dev.IPAddress }}'
```

Make sure that database container is started, show the database pane in PyCharm,
and add a new data source.
PyCharm may complain about missing database drivers.
Install any missing driver files directly through PyCharm or your
distribution's package manager (whatever you prefer).
The password is `password`.

## Setting up the Database ##

For this section, double check that every container is up and running
via `docker-compose ps`, and if necessary run `docker-compose up -d`
again.

Pycroft needs a PostgreSQL database backend.
The unit tests will generate the schema and data automatically,
but usually you want to run your development instance against a recent copy of
our current production database.

The password for the `postgres` user is `password`.

Importing the production database into Pycroft is a three-step process:

1. A regular dump is published in our
   [internal gitlab](https://git.agdsn.de/AGDSN/pycroft-data).

   Clone this repository to your computer.

2. Import the dump:

   `psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft -f ../pycroft-data/pycroft.sql`

After all that, you should be able to log in into your pycroft
instance with the username `agdsn` at `localhost:5000`. All users have the password `password`.

 **Congratulations!**

To import a table from a CSV file, use:

`psql -h 127.0.0.1 -p 55432 -U postgres -d pycroft`

`\copy [tablename] from 'file.csv' with delimiter ',' csv header;"`

## Running the test suite

For the testing setup, there exists a separate docker-compose file:

```sh
# get the stack up and running
docker-compose -f docker-compose.test.yml up -d
# run all the tests
docker-compose -f docker-compose.test.yml run --rm test-app test
# run only the frontend tests
docker-compose -f docker-compose.test.yml run --rm test-app test tests.frontend
```

## Making changes to the database schema

Pycroft uses [Alembic](http://alembic.zzzcomputing.com/) to manage changes to its database schema.
On startup Pycroft invokes Alembic to ensure that the database schema is up-to-date. Should Alembic
detect database migrations that are not yet applied to the database, it will apply them
automatically.

To get familiar with Alembic it is recommended to read the official
[tutorial](http://alembic.zzzcomputing.com/en/latest/tutorial.html).

### Creating a database migration

Migrations are python modules stored under `pycroft/model/alembic/versions/`.

A new migration can be created by running:
```
docker-compose run --rm dev-app alembic revision -m "add test table"
```

Alembic also has the really convenient feature to
[autogenerate](http://alembic.zzzcomputing.com/en/latest/autogenerate.html) migrations,
by comparing the current status of the database against the table metadata of the application.
```
docker-compose run --rm dev-app alembic revision --autogenerate -m "add complex test table"
```

The autogeneration does not know about trigger functions, view definitons or the like.
For this, you can pop up a python shell and compile the statements yourself.
This way, you can just copy-and-paste them into `op.execute()` commands in the
autogenerated schema upgrade.

```python
import pycroft.model as m
from sqlalchemy.dialects import postgresql
print(m.ddl.CreateFunction(m.address.address_remove_orphans)
      .compile(dialect=postgresql.dialect()))
# if the statement itself has no variable like `address_remove_orphans`,
# you can try to extract it from the `DDLManager` instance:
create_stmt, drop_stmt = [(c, d) for _, c, d in m.user.manager.objects
                          if isinstance(c, m.ddl.CreateTrigger)
                          and c.trigger.name == 'TRIGGER_NAME_HERE']
print(create_stmt.compile(dialect=postgresql.dialect()))
print(drop_stmt.compile(dialect=postgresql.dialect()))
```

## Related dependencies
Pycroft has dependencies that are not part of the Pycroft project, but are
maintained by the Pycroft team. Those are:

- [wtforms-widgets](https://github.com/agdsn/wtforms-widgets),
for rendering forms

To make it easier to make changes on these dependencies, they are added as
submodule in the `deps` folder. You need to recursively clone this repo
in order to have them.

You can make changes in these sudmodules and deploy them (in your dev
environment) with:

```
docker-compose run --rm dev-app pip install -r requirements.txt
```

The production build also uses the submodules. Make sure to update the commit
hash of the submodule HEAD if you change something. This will be shown as
unstaged change.

Additionally, new versions can be uploaded to PyPi by following these steps:

- Adjust setup.py (new version number, etc.)
- Run the `distribute.sh` script afterwards in order to
upload the new version to PyPi

## Tips&Tricks with Celery

Tasks can be executed manually as follows:
- run a shell: `docker-compose run --rm dev-app shell`
- activate the venv: `. ~/venv/bin/activate`
- run a `celery` command: `celery -A pycroft.task call pycroft.task.execute_scheduled_tasks`

If any issues come up, ensure that the `dummy-worker` is not started
and restart the actual celery worker.

## Troubleshooting

Due to laziness, prefix every bash-snippet with
```sh
alias drc=docker-compose
```

### Webpack appears to be missing a library

Re-Install everything using npm, and re-run the webpack entrypoint.

```sh
drc run --rm dev-app shell npm ci
drc run --rm dev-app webpack
```


### Pip appears to be missing a dependency

Reinstall the pip requirements

```sh
drc run --rm dev-app pip install -r requirements.txt
```

### I need to downgrade the schema

```
drc run --rm dev-app alembic downgrade $hash
```


### Other problems (f.e. failing database initialization)

```
drc build
```
