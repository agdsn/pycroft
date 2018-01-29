# About #

Pycroft is the future user management system of the AG DSN student
network.  It is based on [Flask](http://flask.pocoo.org) and expects a
postgres database making use of the
[SQLAlchemy ORM](http://www.sqlalchemy.org/).

# Cloning this directory #

A basic understanding of [git](https://git-scm.com/) is advisable.
The first step should be to clone this repository via `git clone
<url>`, using what clone url shows you above
[this very readme](https://github.com/agdsn/pycroft)

# Running a Test instance (Docker+Compose) #

An easy way of doing the setup is by using docker-compose.

## Installing Docker and docker-compose ##

Follow the
guides [here](https://www.docker.com/community-edition#download)
and [here](https://docs.docker.com/compose/install/).
You will need a docker engine of `1.10.0+` and a docker compose
version of `1.8.0+` (I am not sure which exact version introduced
version 2 of the config)

Also, note that you might have to add your user to the `docker` group
for running docker as a non-root:

```sh
sudo usermod -aG docker $(whoami)
su $(whoami)  # to re-login as yourself to use the new groups
```

Note that if you start e.g. pycharm without logging out and in again,
the docker group will not have been applied yet.

You should now be able to run `docker-compose config` and see the
current configuration.

## Building and running the services ##

There are multiple setups defined in multiple files:

* `docker-compose.yml`: A minimal setup consisting of a python and a
  postgresql container for running the web server.  This has
  everything you need initially.
* `docker-compose.testing.yml`: A setup with an ldap container, a
  rabbitmq container and a celery worker (mocking the Hades RPC
  interface) used for integration tests
* `docker-compose.travis.yml`: Basically the same as `testing`, but
  without volumes (i.e. mounting of your source directory into the
  relevant containers)

Different docker-compose setups defined in different files can be
accessed using the `-f` switch like `docker-compose -f
docker-compose.testing.yml ps`.  The default file, i.e. the one used
when omitting the `-f` switch, is `docker-compose.yml`.  This is the
only one you need in order to set up an example pycroft instance.

Said default setup provides:

* web: The container running the webservice.  This includes all python
  libraries as well as bower for the installation of the js
  dependencies.  Instead of using the project directory from inside
  the container, however, your project directory (`./`) will be
  mounted there, so you don't have to rebuild the container's image
  after every tiny change.  As the server is started with `--debug`,
  it will automatically reload when it detects a change to the project
  files.
* db: A postgres database to be used for the pycroft database and the
  legacy cache.

Because the web container mounts the project directory on your machine,
you want to ensure that the user id (UID) and group id (GID) on your
machine matches with the UID/GID of the `pycroft` user inside the container,
otherwise the user inside the container might not be able to read/write files
or you might not be able to read/write files created by the container.

The web container has build arguments for the UID and GID of the user inside
the container. The defaults for these arguments is 1000/1000. You can specify
the these build arguments manually on the command-line, when you create the
container with `docker build` or `docker-compose build`. The compose file will
however automatically use the environment variables `UID` and `GID` if set and
not empty.

Don't be fooled by your shell however by executing the following command and
feeling safe, if it outputs your UID:

```bash
echo $UID
```

Bash and zsh automatically define this variable, but do not export it:

```bash
python3 -c 'import os; print(os.getenv("UID"))'
```

The easiest thing therefore is to set `UID` in your shell, by setting

```bash
export UID
# Bash does not set GID, zsh does, so you can omit the assignment with zsh:
export GID=$(id -g)
```

You should put these lines somewhere in your shell's startup script (e.g.
`.profile`), so that it is always defined.

Alternatively you can use `docker-compose`'s override mechanism and create
your own `docker-compose.override.yml` and set the UID/GID build argument
there.

## Pycharm Integration

In order to integrate the setup into pycharm, make sure you updated,
there were important bugfixes.

### Project interpreters

The source code provides two running configurations, one for running
the test instance, and one for unittesting.  In order for them to work
correctly, we need to add two project interpreters, which will
represent the corresponding docker-compose setup.

Go to “Settings” → “Project interpreters” → Gear icon → “Add remote” →
“Docker Compose”.

Create a new server (use the default settings for that) if noone
exists yet.  Add the config file `compose/default/docker-compose.yml`.
Select service: `web` and python interpreter: `python3`.

Repeat the same thing for `compose/testing/docker-compose.yml`.

Save, and make sure the correct interpreter (`/default/`, not
`/testing/`) is selected as default for the project (“Project
settings” → “Project interpreter”).  As a proof of concept, you can
run a python console.

### Database connections (optional)

Open the database window and open the preferences. Install any missing
driver files.  Although the password should be set and remembered, for
some reason pycharm may ask you anyway.  The password is `password`.

### Things left to do

Just as in the manual setup described below, you will need to import
the legacy dump so the test instance has a data foundation.


## The pure docker way

After having installed docker and docker-compose, you can now start
all of the services (the `-d` stands for “detached”).  This pulls the
postgres image and builds the one for pycroft.  Since a whole
production system is going to be set up, this may take a few minutes,
so grab a cup of tea and relax.

```sh
docker-compose up -d
```

Every container should now be marked as `UP` if you take a look at
`docker-compose ps`.  There you see which port forwardings have been
set up (remember the port `web` has been exposed!)

Because you started them in detached mode, you will not see what they
print to stdout.  You can inspect the output like this:

```sh
docker-compose logs # for all services
docker-compose logs web  # for one service
docker-compose logs -f --tail=50 web  # Print the last 50 entries and follow the logs
```

The last command should tell you that the server spawned an instance
at 0.0.0.0:5000 from inside the container.  Due to the port
forwarding, you can take a peek at a working UI by accessing
`0.0.0.0:5001` from your browser.

**But don't be too excited, pycroft will fail after the login – we
have to set up the database.**

## Setting up the Database ##

For this section, double check that every container is up and running
via `docker-compose ps`, and if necessary run `docker-compose up -d`
again.

Pycroft needs a database in the backend.  Because currently, the
schema isn't fixed and can change regularly (it actually does), it is
easier to provide a dump of data to feed into the legacy importer
(`legacy/import_legacy.py`).  The legacy importer translates data from
a cache database into the pycroft schema.  The cached data is
retrieved using the legacy cacher, which accumulates data from our
ldap, mysql and postgres databases into one big cache database, a
regular dump of which is published in our
[internal gitlab](https://git.agdsn.de/team-services/pycroft-data).

Once you got that dump (if you cloned the repo, pull the latest
changes), make sure it is placed somewhere in your source directory.
Let's assume this location is `/example/legacy.sql`.  Because the
whole source directory is mounted into the `db` container to
`/pycroft`, we can import it from inside:

```sh
docker-compose exec --user postgres db psql -f /pycroft/example/legacy.sql
```

You successfully included your legacy dump into the docker-container!
Now, you need to convert it into a pycroft database with the pycroft
importer.  This is done by running `/legacy/import_legacy.py` in a
separate container:

```sh
docker-compose stop web  # this container blocks the /postgres db
docker-compose run --rm web python3 -m legacy.import_legacy
docker-compose start web
```

This will take some time as well, as you will be translating more than
400k financial records using an abstracted ORM backend.

Before we congratulate ourselves, let's dump the contents of the
`pycroft` database just to be sure we don't have to run the importer
again (except someone changes the schema, then you'll have to do it
regardless).  This is more tricky since the `postgres` user from
inside the container does not have write permissions on the mounted
directory by default:

```sh
docker-compose exec --user postgres db pg_dump --create --clean --if-exists postgres:///pycroft -f /tmp/pycroft.sql
docker cp pycroft_db_1:/tmp/pycroft.sql ./example/pycroft_$(date +%Y-%m-%d).sql
docker-compose exec db rm /tmp/pycroft.sql
```

The “weird” container name in the second command arises from the need
to talk to containers directly via _docker_ instead of operating on
the _service_ (here: `db`) using _docker-compose_.  You will find the
current container name to a running service with `docker-compose ps`.

If you want to re-import the dump, import it like the legacy database just with

```sh
docker-compose exec --user postgres db psql -f /pycroft/example/pycroft_2017-05-03_no_pw.sql
```

After all that, you should be able to log in into your pycroft
instance at `0.0.0.0:5001`!  **Congratulations!**

## Running the test suite

For the testing setup, there exists a separate docker-compose file:

```sh
# get the stack up and running
docker-compose -f docker-compose.testing.yml up -d
# run all the tests
docker-compose -f docker-compose.testing.yml run --rm web nosetests -v
# run only the frontend tests
docker-compose -f docker-compose.testing.yml run --rm web nosetests -v tests.frontend
```


# Running a Test instance (Vagrant) #

**This is not the recommended way anymore, except you know what you
do!** _(even if you know what you do, most of the integration tests'
backends (ldap, rabbitmq) haven't been backported to the vagrant
setup.)_

A vagrant box using a docker container has been pre-configured.  Once
having installed vagrant and docker, `vagrant up` starts the
container.  This does not start the webserver yet! It has to be
manually invoked, either using pycharm and selecting the `Web
Postgres` run configuration, or by manually invoking the start script.
For the latter, see the section below.  In any case, the server should
be accessible on `0.0.0.0:5000` (`127.0.0.1` works as well for the
server itself, you can't use the builtin debugger however because
authentication somehow isn't passed that way.)

## Getting some Data ##

However, pycroft expects being bound to a database, which we haven't
set up yet.  The easiest way to do this is being an active member and
using the importer.  Because Pycroft is still in development, the
database schema changes a lot, and thus checking in and maintaining
example data has proved unfeasible.

Since pycroft uses an importer to cache and then import data from the
legacy system, a dump of said cached data is being maintained in our
[internal gitlab](https://git.agdsn.de/team-services/pycroft-data).

## What databases are there? ##

In the container, there are three databases in use (although perhaps
not yet created):

* `pycroft`: This is where the web app expects its actual data.
* `pycroft_test`: This is where the unittests (if using postgres) expect
* `legacy`: This is where `legacy/cache_legacy.py` deposits legacy
  data from the legacy backends (netusers(mysql), userman(postgres),
  ldap(planned/in progress)), and where `legacy/import_legacy.py`
  reads the data from.

The latter is where the sql dump should be inserted.

## The Docker container ##

Let's start it:

```sh
$ vagrant up
# …
$ vagrant ssh
```

The first command started the container, which starts services such as
sshd.  The second presents you a shell.  Under `/vagrant`, the
directory where you cloned pycroft into is mounted
(bi-directionally!).  You can thus place the dump e.g. in a folder called `example`.

```sh
$ vagrant ssh
$ cd /vagrant
$ psql < example/legacy.sql
# psql resposnses…
$ cd legacy
$ cp conn.py.example conn.py
# because you're just importing a dump, you don't need to edit the conn.py!
$ python import_legacy.py
```

Note that importing takes an enormous amount of time. There are
hundreds of thousands of financial records which have to be processed!
Grab a ~~cup of coffee~~ bottle of Mate and relax.

If that's done, you can start the web server.

You should immediately dump the pycroft database using pgdump!
Because the postgres instance runs in the docker container, which is
considered stateless and thus may lose changes to the file system in
many circumstances, halting vagrant and reupping it loses the data you
just so hardly imported.

For the next time you start pycroft, it is easier to just import your
freshly dumped `pycroft.sql` into the `pycroft` database.


## Custom setup ##

The web server can be started in a custom manner by starting `python
/vagrant/server_run.py --debug --exposed` in the vagrant ssh session,
given that `PYCROFT_DB_URI` is set in the environment.  The value
should be
`postgresql+psycopg2:///pycroft?host=/postgresql&client_encoding=utf8"`.

The `--exposed` is necessary to not restrict the web server for
container-internal access only and be able to let vagrant pass port
5000 to the host machine.
