# -*- coding: utf-8 -*-
"""
    console.view
    ~~~~~~~~~~~~~~

    This module is a simple command line client.
    Invoke this file with python -m console.console

    IMPORTANT: If you want to create a database,
               be sure all modules are imported

    :copyright: (c) 2012 by AG DSN.
"""

import code
from pycroft import model
from pycroft.model import accounting, base, dormitory, finance, hosts, logging
from pycroft.model import ports, rights, user
from pycroft.model.dormitory import Dormitory
from pycroft.model.session import session


def createDB():
    model.create_db_model()
    session.flush()


def dropDB():
    model.drop_db_model()
    session.flush()


def newDorm():
    """Make a new dormitory"""

    street = u_input("street: ")
    number = u_input("number: ")
    short_name = u_input("short_name: ")

    try:
        new_dormitory = Dormitory(number=number, short_name=short_name,
            street=street)
    except:
        print("could not create dormitory")

    print new_dormitory

    confirm = raw_input("do you want to save? (y/n): ")

    if confirm == "y":
        try:
            session.add(new_dormitory)
            session.commit()
        except:
            session.rollback()
            raise


def deleteDorm():
    """Delete a existing dormitory from the list"""

    dormitories = session.query(Dormitory).all()

    if not len(dormitories):
        print "no dormitories"
        return

    for i in range(len(dormitories)):
        print i
        print dormitories[i]

    while True:
        try:
            delete = int(raw_input("(you have to confirm) delete No. : "))
            break
        except ValueError:
            print "you have to type a number"

    if not delete >= 0 or not delete < len(dormitories):
        print "{} is not a dormitory".format(delete)
        return

    print dormitories[delete]
    confirm = raw_input("do you want to delete this dormitory? (y/n): ")

    if confirm == "y":
        try:
            session.delete(dormitories[delete])
            session.commit()
            print "deleted"
            return
        except:
            session.rollback()

def h():
    print "\nCommands:"
    print "createDB()   - create database"
    print "dropDB()     - delete database"
    print "h()          - shows this help"
    print "newDorm()    - new dormitory"
    print "deleteDorm() - delete a dormitory"
    print "quit()       - quits the program"
    print ""


def u_input(promt):
    """promt for utf-8 unicode object"""
    return unicode(raw_input(promt), "utf-8")

###############################################################################

# start the interpreter
code.interact(
    banner="Pycroft 0.1 \n# type h() for help #",
    local=locals())
