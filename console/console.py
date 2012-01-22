# -*- coding: utf-8 -*-
"""
    console.view
    ~~~~~~~~~~~~~~

    This module is a simple command line client.
    Invoke this file with python -m console.console

    :copyright: (c) 2012 by AG DSN.
"""

import code
import sys
#from pycroft.helpers.user_controller import UserController
from pycroft.model.dormitory import Dormitory


def createDB():
    from pycroft import model
    model.create_db_model()
    model.session.session.flush()


def dropDB():
    from pycroft import model
    model.drop_db_model()
    model.session.session.flush()


def newDorm():

    street = raw_input("street: ")
    number = raw_input("number: ")
    short_name = raw_input("short_name: ")

    try:
        new_dormitory = Dormitory(number=number, short_name=short_name,
            street=street)
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise

    print str(new_dormitory)

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




def help():
    print '\nCommands:'
    print 'createDB() - create database'
    print 'dropDB() - delete database'
    print '\thelp() - shows this help'
    print '\tnewDorm() - new dormitory'
    print '\tnewRoom() - new room'
    print '\tnewUser() - new user'
    print '\tquit() - quits the program'
    print ''

################################################################################

# start the interpreter
code.interact(
    banner='Pycroft 0.1 \n# type help() for help #',
    local=locals())