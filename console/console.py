# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    console.view
    ~~~~~~~~~~~~~~

    This module is a simple command line client.
    Invoke this file with python -m console.console

    :copyright: (c) 2012 by AG DSN.
"""

import code
#from pycroft.helpers.user_controller import UserController
from pycroft.model.dormitory import Dormitory
from pycroft.model.session import session


def createDB():
    from pycroft import model
    model.create_db_model()
    model.session.session.flush()


def dropDB():
    from pycroft import model
    model.drop_db_model()
    model.session.session.flush()


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
        raise

    print(str(new_dormitory))

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
        print("no dormitories")
        return

    for i in range(len(dormitories)):
        print(i)
        print u'%s' % dormitories[i]

    try:
        delete = int(raw_input("(you have to confirm) delete No. : "))
    except:
        print("is not a number")
        raise

    if not delete >= 0 or not delete < len(dormitories):
        print(str(delete) + " is not a dormitory")
        return

    print u'%s' % dormitories[delete]
    confirm = raw_input("do you want to delete this dormitory? (y/n): ")

    if confirm == "y":
        try:
            session.delete(dormitories[delete])
            session.commit()
        except:
            session.rollback()
            raise


def newRoom():
    pass


def newUser():

    #name = raw_input("name: ")
    #dorm_short_name = raw_input("dormitory: ")
    #floor_no = raw_input("floor no.: ")
    #room_no = raw_input("room no.: ")
    #login = raw_input("login: ")
    #mac = raw_input("mac: ")

    # returns new user
    #try:
    #    user = UserController.new_user(name,
    #       dorm_short_name, floor_no, room_no, login, mac)
    #except:
    #    print "Unexpected error:", sys.exc_info()[0]
    #    raise

    # print new user
    #print str(user)

    # do you want to safe?
    # yes
    # change
    # no
    pass


def h():
    print "\nCommands:"
    print "createDB()   - create database"
    print "dropDB()     - delete database"
    print "h()          - shows this help"
    print "newDorm()    - new dormitory"
    print "deleteDorm() - delete a dormitory"
    #print "newRoom()    - new room"
    #print "newUser()    - new user"
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
