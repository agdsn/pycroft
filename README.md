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


# Running a Test instance #

To set up a working pycroft server, it is advised to use
[Vagrant](https://www.vagrantup.com/).  A vagrant box using a docker
container has been pre-configured.  Once having installed vagrant and
docker, `vagrant up` starts the container.  This does not start the
webserver yet! It has to be manually invoked, either using pycharm and
selecting the `Web Postgres` run configuration, or by manually
invoking the start script.  For the latter, see the section below.  In
any case, the server should be accessible on `0.0.0.0:5000`
(`127.0.0.1` works as well for the server itself, you can't use the
builtin debugger however because authentication somehow isn't passed
that way.)

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


# Custom setup #

The web server can be started in a custom manner by starting `python
/vagrant/server_run.py --debug --exposed` in the vagrant ssh session,
given that `PYCROFT_DB_URI` is set in the environment.  The value
should be
`postgresql+psycopg2:///pycroft?host=/postgresql&client_encoding=utf8"`.

The `--exposed` is necessary to not restrict the web server for
container-internal access only and be able to let vagrant pass port
5000 to the host machine.
