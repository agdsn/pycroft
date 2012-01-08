# -*- coding: utf-8 -*-
"""
    console.view
    ~~~~~~~~~~~~~~

    This module is a simple command line client.

    :copyright: (c) 2012 by AG DSN.
"""

import sys
#from pycroft.controller.user_controller import UserController
from pycroft.model.dormitory import Dormitory


class View:
    """ View the console client
    """

    def newDormitory(self):

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

    def newRoom(self):
        pass

    def newUser(self):

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

    def run(self):

        print 'Pycroft 0.1\n# type help(h) for help #\n'

        #main loop
        while True:
            command = raw_input("> ")

            if command == 'h' or command == 'help':
                self.print_help()
            elif command == 'nd' or command == 'newdorm':
                self.newDormitory()
            elif command == 'nr' or command == 'newroom':
                self.newRoom()
            elif command == 'nu' or command == 'newuser':
                self.newUser()
            elif command == 'q' or command == 'quit':
                sys.exit(0)
            else:
                print 'command unknown'

    def print_help(self):
        print '\nCommands:'
        print '\thelp(h) - shows this help'
        print '\tnewdorm(nd) - new dormitory'
        print '\tnewroom(nr) - new room'
        print '\tnewuser(nu) - new user'
        print '\tquit(q) - quits the program'
        print ''


view = View()
view.run()
