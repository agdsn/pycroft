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

ASSETS_DIRECTORY = join(dirname(__file__), 'assets')
ASSETS_LOGO_FILENAME = join(ASSETS_DIRECTORY, 'logo.png')


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
                            topMargin=2 * cm,
                            bottomMargin=2 * cm)
    style = getStyleSheet()
    story = []

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

    stylesheet.add(ParagraphStyle(name='Bold',
                                  parent=stylesheet['BodyText'],
                                  fontName="Helvetica-Bold"))

    return stylesheet
