# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from io import BytesIO
from os.path import dirname, join

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import StyleSheet1, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT

ASSETS_DIRECTORY = join(dirname(__file__), 'assets')
ASSETS_LOGO_FILENAME = join(ASSETS_DIRECTORY, 'logo.png')
ASSETS_EMAIL_FILENAME = join(ASSETS_DIRECTORY, 'email.png')
ASSETS_FACEBOOK_FILENAME = join(ASSETS_DIRECTORY, 'facebook.png')
ASSETS_TWITTER_FILENAME = join(ASSETS_DIRECTORY, 'twitter.png')
ASSETS_WEB_FILENAME = join(ASSETS_DIRECTORY, 'web.png')
ASSETS_HOUSE_FILENAME = join(ASSETS_DIRECTORY, 'house.png')


def generate_user_sheet(user, user_id, plain_password):
    """Create a „new member“ datasheet for the given user

    :param User user: A pycroft user
    :param str user_id: The user's ID.  It has to be given extra,
        because the user_id is not appearent given the ORM object
        itself; encoding is done in the library.
    :param str plain_password: The password
    """
    # Anlegen des PDF Dokuments, Seitengröße DIN A4 Hochformat)
    buf = BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=2 * cm,
                            leftMargin=2 * cm,
                            topMargin=0.5 * cm,
                            bottomMargin=2 * cm)
    style = getStyleSheet()
    story = []

    PAGE_WIDTH = defaultPageSize[0]
    PAGE_HEIGHT = defaultPageSize[1]

    story.append(
        Paragraph('{dorm}<br/>{name}<br/>{level}/{room}'.format(
            dorm=str(user.room.building.short_name),
            name=user.name,
            level=str(user.room.level),
            room=str(user.room.number)
        ),
                  style['RightText']))

    im = Image(ASSETS_LOGO_FILENAME, 5 * cm, 5 * cm)
    story.append(im)
    story.append(HRFlowable(width="100%",
                            thickness=3,
                            color=black,
                            spaceBefore=0.8 * cm,
                            spaceAfter=0.8 * cm))

    story.append(
        Paragraph('Welcome as a member of the AG DSN, {}!'
                  .format(user.name),
                  style['BodyText']))

    story.append(
        Paragraph('We are proud to announce that your network access has been '
                  'activated. If you encounter any problems, drop us a mail or '
                  'visit us during our office hours. You can find contact '
                  'information at the bottom of this page.',
                  style['BodyText']))

    story.append(
        Paragraph('Please make sure to pay your membership contribution in time.'
                  ' You can find further details on our web page.',
                  style['Bold']))

    story.append(Paragraph('Wishing you all the best,', style['BodyText']))
    story.append(Paragraph('Your AG DSN', style['BodyText']))
    story.append(HRFlowable(width="100%",
                            thickness=3,
                            color=black,
                            spaceBefore=0.8 * cm,
                            spaceAfter=0.8 * cm))

    ips = []
    macs = []
    for user_host in user.hosts:
        for ip in user_host.ips:
            ips.append(str(ip.address))
            macs.append(ip.interface.mac)

    data = [['Name:', user.name, 'User-ID:', user_id],
            ['Username:', user.login, 'IPv4-Address:', ', '.join(ips)],
            ['Password:', plain_password, 'MAC-Address:', ', '.join(macs)],
            ['E-Mail:', user.email, 'Location:', str(user.room)]]
    t = Table(data, colWidths=[pdf.width * 0.15, pdf.width * 0.34] * 2)

    story.append(t)
    story.append(HRFlowable(width="100%", thickness=3, color=black, spaceBefore=0.8 * cm,
                            spaceAfter=0.8 * cm))

    # Footer
    im_web = Image(ASSETS_WEB_FILENAME, 0.4 * cm, 0.4 * cm)
    im_house = Image(ASSETS_HOUSE_FILENAME, 0.4 * cm, 0.4 * cm)
    im_email = Image(ASSETS_EMAIL_FILENAME, 0.4 * cm, 0.4 * cm)
    im_fb = Image(ASSETS_FACEBOOK_FILENAME, 0.4 * cm, 0.4 * cm)
    im_t = Image(ASSETS_TWITTER_FILENAME, 0.4 * cm, 0.4 * cm)
    data = [
        [im_web, 'Website:', im_house, 'Wundtstraße 5', im_house, 'Hochschulstr. 46', im_house, 'Borsbergstr. 34'],
        ['', 'https://agdsn.de', '', 'Doorbell 0100', '', 'Basement', '', '7th floor'],
        ['', '', '', '01217 Dresden', '', '01069 Dresden', '', '01309 Dresden'],
        ['', '', '', '', '', '', '',''],
        [im_email, 'support@agdsn.de', '', 'Office hours:', '', 'Office hours:', '', 'Office hours:'],
        [im_fb, '/DresdnerStudentenNetz', '', 'Mon, 7pm - 8pm', '', 'Mon, 7pm - 7.30pm', '', 'Mon, 8pm - 9pm'],
        [im_t, '/ag_dsn', '', 'Thu, 7pm - 8pm', '', 'Thu, 7pm - 7.30pm', '', 'Thu, 8pm - 9pm']
    ]

    rowHeight = 0.4*cm
    t = Table(data, colWidths=[0.5*cm, 3.5*cm, 0.5*cm, 3.5*cm, 0.5*cm, 3.5*cm, 0.5*cm, 3.5*cm],
              rowHeights=[rowHeight, rowHeight, rowHeight, rowHeight, rowHeight, rowHeight, rowHeight],
              hAlign='CENTER'
    )
    story.append(t)

    story.append(
        Paragraph('''<b>Interested in our work?</b>
        In the podcast MultiCast you can hear about the latest developments and
        our day-to-day work in the students network: https://podcast.agdsn.de/''',\
                  style['JustifyText']))

    story.append(Paragraph('''<b>Join us:</b>\nThe student network was created and is run by students like yourself. If you are interested in our work don’t 
hesitate to visit us at our office. There are many ways of contribution to our cause without the need of being a 
computer science engineer. Just to mention some possible of contributions: Administration and finances, network
maintenance, software development and many more. Besides, you can add some extra extracurricular 
activity to your CV and have the opportunity to see and work with usually hidden technology. We would be 
happy to welcome you with us. Be our guest at our office hours.''', style['JustifyText']))

    # PDF generieren und speichern
    pdf.build(story)

    return buf.getvalue()


def getStyleSheet():
    """Returns a stylesheet object"""
    stylesheet = StyleSheet1()

    stylesheet.add(ParagraphStyle(name='Normal',
                                  fontName="Helvetica",
                                  fontSize=10,
                                  leading=12))

    stylesheet.add(ParagraphStyle(name='BodyText',
                                  parent=stylesheet['Normal'],
                                  spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='RightText',
                                  parent=stylesheet['Normal'],
                                  alignment=TA_RIGHT,
                                  spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='JustifyText',
                                 parent=stylesheet['Normal'],
                                 alignment=TA_JUSTIFY,
                                 spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='Bold',
                                  parent=stylesheet['BodyText'],
                                  fontName="Helvetica-Bold"))

    return stylesheet
