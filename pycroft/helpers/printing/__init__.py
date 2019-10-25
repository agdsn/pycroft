# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
from io import BytesIO
from os.path import dirname, join

from reportlab.lib.colors import black
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import StyleSheet1, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Table, Spacer
from reportlab.platypus.flowables import HRFlowable, PageBreak
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.rl_config import defaultPageSize
from reportlab.lib.enums import TA_JUSTIFY, TA_RIGHT, TA_CENTER
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from pycroft.model.finance import BankAccount
from pycroft import config

ASSETS_DIRECTORY = join(dirname(__file__), 'assets')
ASSETS_LOGO_FILENAME = join(ASSETS_DIRECTORY, 'logo.png')
ASSETS_EMAIL_FILENAME = join(ASSETS_DIRECTORY, 'email.png')
ASSETS_FACEBOOK_FILENAME = join(ASSETS_DIRECTORY, 'facebook.png')
ASSETS_TWITTER_FILENAME = join(ASSETS_DIRECTORY, 'twitter.png')
ASSETS_WEB_FILENAME = join(ASSETS_DIRECTORY, 'web.png')
ASSETS_HOUSE_FILENAME = join(ASSETS_DIRECTORY, 'house.png')

def generate_user_sheet(user, user_id, plain_password, generation_purpose=''):
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
                            rightMargin=1.5 * cm,
                            leftMargin=1.5 * cm,
                            topMargin=0.5 * cm,
                            bottomMargin=0.5 * cm)
    style = getStyleSheet()
    story = []

    PAGE_WIDTH = defaultPageSize[0]
    PAGE_HEIGHT = defaultPageSize[1]

    # HEADER
    im_web = Image(ASSETS_WEB_FILENAME, 0.4 * cm, 0.4 * cm)
    im_house = Image(ASSETS_HOUSE_FILENAME, 0.4 * cm, 0.4 * cm)
    im_email = Image(ASSETS_EMAIL_FILENAME, 0.4 * cm, 0.4 * cm)
    im_fb = Image(ASSETS_FACEBOOK_FILENAME, 0.4 * cm, 0.4 * cm)
    im_t = Image(ASSETS_TWITTER_FILENAME, 0.4 * cm, 0.4 * cm)
    im_logo = Image(ASSETS_LOGO_FILENAME, 3.472 * cm, 1 * cm)

    if user.room:
        shortinfo = Paragraph('{dorm}<br/>{name}<br/>{level}/{room}'.format(
            dorm=str(user.room.building.short_name),
            name=user.name,
            level=str(user.room.level),
            room=str(user.room.number)
        ), style['RightText'])
    else:
        shortinfo = Paragraph('{name}'.format(
            name=user.name
        ), style['RightText'])

    data = [
        [im_web, 'https://agdsn.de', im_t, '/ag_dsn'],
        [im_email, 'support@agdsn.de', im_fb, '/DresdnerStudentenNetz']
    ]
    social = Table(data, colWidths=[0.5 * cm, 3.5 * cm, 0.5 * cm],
                   rowHeights=[0.5 * cm] * 2)

    data = [[im_logo, social, shortinfo]]
    t = Table(data, colWidths=[3.972 * cm, 9.5 * cm, 4 * cm],
              style=[
                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ])
    story.append(t)

    story.append(HRFlowable(width="100%",
                            thickness=1,
                            color=black,
                            spaceBefore=0.0 * cm,
                            spaceAfter=0.5 * cm))

    welcome = Paragraph('''Welcome as a member of the AG DSN, {}!
We are proud to announce that your network access has been activated. If you encounter any problems, drop us a mail or visit us during our office hours. You can find contact information below on this page.'''
                  .format(user.name),
                  style['BodyText'])

    return_notice = Paragraph(
        '''<font size="9pt">Nicht nachsenden!</font>''',
        style['Normal'])
    sender = Paragraph(
        '''<font size="9pt">AG DSN • Support • Wundtstraße 5 • 01217 Dresden</font>''',
        style['Normal'])
    address = f"{user.name}\n{user.address:long}"
    data = [
        [None, None],
        [return_notice, None],
        [sender, None],
        [address, welcome]
    ]
    addressTable = Table(data, colWidths=[9 * cm, pdf.width - 9*cm],
                   rowHeights=[1*cm, 0.3*cm, 0.8*cm, 3 * cm], style=[
                  ('VALIGN', (0, 0), (-1, -1), 'TOP'),
              ])
    story.append(addressTable)

    story.append(
        HRFlowable(width="100%", thickness=3, color=black, spaceBefore=0.4 * cm,
                   spaceAfter=0.6 * cm))

    macs = []
    for user_host in user.hosts:
        for ip in user_host.ips:
            macs.append(ip.interface.mac)

    need_explicit_address = not user.room or user.room.address != user.address
    data = [['Name:', user.name, 'User-ID:', user_id],
            ['Username:', user.login, 'MAC-Address:', ', '.join(macs)],
            ['Password:', plain_password,
             'Dorm Location:' if need_explicit_address else 'Location:',
             str(user.room) if user.room else ""],
            ['E-Mail:', user.email, "", ""]]
    if need_explicit_address:
        data.append(['Address:', user.address])
    t = Table(data,
              style=[
                  ('FONTNAME', (1, 2), (1, 2), 'Courier'),
              ],
              colWidths=[pdf.width * 0.15, pdf.width * 0.34] * 2, )

    story.append(t)
    story.append(
        HRFlowable(width="100%", thickness=3, color=black, spaceBefore=0.4 * cm,
                   spaceAfter=0.6 * cm))

    # offices
    im_web = Image(ASSETS_WEB_FILENAME, 0.4 * cm, 0.4 * cm)
    im_house = Image(ASSETS_HOUSE_FILENAME, 0.4 * cm, 0.4 * cm)
    im_email = Image(ASSETS_EMAIL_FILENAME, 0.4 * cm, 0.4 * cm)
    im_fb = Image(ASSETS_FACEBOOK_FILENAME, 0.4 * cm, 0.4 * cm)
    im_t = Image(ASSETS_TWITTER_FILENAME, 0.4 * cm, 0.4 * cm)
    data = [
        ['', im_house, 'Wundtstraße 5', im_house, 'Hochschulstr. 50', im_house,
         'Borsbergstr. 34'],
        ['', '', 'Doorbell 0100', '', 'Ground floor', '', '7th floor'],
        ['', '', '01217 Dresden', '', '01069 Dresden', '', '01309 Dresden'],
        ['', '', '', '', '', '', ''],
        ['Office hours:', '', 'Mon, 7pm - 8pm', '', 'Mon, 7pm - 7.30pm', '',
         'Mon, 8pm - 9pm'],
        ['', '', 'Thu, 7pm - 8pm', '', 'Thu, 7pm - 7.30pm', '',
         'Thu, 8pm - 9pm']
    ]

    rowHeight = 0.4 * cm
    t = Table(data, colWidths=[2.5 * cm, 0.5 * cm, 3.5 * cm, 0.5 * cm, 3.5 * cm,
                               0.5 * cm, 3.5 * cm],
              rowHeights=[rowHeight, rowHeight, rowHeight, rowHeight, rowHeight,
                          rowHeight],
              hAlign='CENTER'
              )
    story.append(t)

    story.append(
        Paragraph('''<b>Interested in our work?</b>
                In the podcast MultiCast you can hear about the latest developments and
                our day-to-day work in the students network: https://podcast.agdsn.de/''', \
                  style['JustifyText']))

    story.append(Paragraph('''<b>Join us:</b>\nThe student network was created and is run by students like yourself. If you are interested in our work don’t 
        hesitate to visit us at our office. There are many ways of contribution to our cause without the need of being a 
        computer science engineer. Just to mention some possible contributions: Administration and finances, network
        maintenance, software development and many more. Besides, you can add some extra extracurricular 
        activity to your CV and have the opportunity to see and work with usually hidden technology. We would be 
        happy to welcome you with us. Be our guest at our office hours.''',
                           style['JustifyText']))

    story.append(
        HRFlowable(width="100%", thickness=3, color=black, spaceBefore=0.4 * cm,
                   spaceAfter=0.4 * cm))

    # Payment details
    contribution = 500  # monthly membership contribution in EUR
    story.append(Paragraph('''<b>Payment details:</b> As a member, you have to transfer a monthly contribution of {0:1.2f}€ to our bank account.
        Paying cash is not possible. The contribution is due at the end of each month. You can pay as much in advance as you want, we will simply subtract
        the monthly contribution at the end of each month. We recommend that you pay at the beginning of each semester in advance, meaning you transact
        six monthly contributions at once.'''.format(
        (contribution / 100)), style['JustifyText']))

    bank = BankAccount.q.filter_by(account_number='3120219540').first()
    bank = config.membership_fee_bank_account

    recipient = 'Studierendenrat TUD - AG DSN'

    if user.room:
        purpose = '{id}, {name}, {dorm} {level} {room}'.format(
            id=user_id,
            name=user.name,
            dorm=str(user.room.building.short_name),
            level=str(user.room.level),
            room=str(user.room.number)
        )
    else:
        purpose = '{id}, {name}'.format(
            id=user_id,
            name=user.name
        )

    amount = contribution / 100
    data = [
        ['Beneficiary:', recipient],
        ['Bank:', bank.bank],
        ['IBAN:', bank.iban],
        ['BIC:', bank.bic],
        ['Purpose/Intended use/\nDescription:', purpose],
        ['Amount', '{0:1.2f}€'.format(amount)]
    ]
    payment_table = Table(data, colWidths=[4 * cm, 4 * cm],
                          style=[
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                          ])

    qr_size = 4 * cm
    qr_code = qr.QrCodeWidget(
        generate_epc_qr_code(bank, recipient, amount, purpose))
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    girocode = Drawing(qr_size, qr_size,
                       transform=[qr_size / width, 0, 0, qr_size / height, 0,
                                  0])
    girocode.add(qr_code)

    data = [[payment_table, girocode]]
    t = Table(data, colWidths=[13 * cm, 4 * cm],
              style=[
                  ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
              ])
    story.append(t)

    story.append(
        Paragraph(
            '<i>Scan the QR-Code with your banking app to import the payment details.</i>',
            style['CenterText'])
    )

    if generation_purpose:
        generation_purpose = ' ({})'.format(generation_purpose)
    story.append(
        Paragraph(
            '<i>Generated on {date}{purpose}</i>'.format(
                date=datetime.date.today(),
                purpose=generation_purpose
            ),
            ParagraphStyle(name='SmallRightText',
                           parent=style['Normal'],
                           alignment=TA_RIGHT,
                           fontSize=8,
                           spaceBefore=15))
    )

    # PDF generieren und speichern
    pdf.build(story)

    return buf.getvalue()


def generate_wifi_user_sheet(user, user_id, plain_password):
    """Create a „wifi“ datasheet for the given user

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
                            bottomMargin=0.5 * cm)
    style = getStyleSheet()
    story = []

    PAGE_WIDTH = defaultPageSize[0]
    PAGE_HEIGHT = defaultPageSize[1]

    # HEADER
    im_web = Image(ASSETS_WEB_FILENAME, 0.4 * cm, 0.4 * cm)
    im_house = Image(ASSETS_HOUSE_FILENAME, 0.4 * cm, 0.4 * cm)
    im_email = Image(ASSETS_EMAIL_FILENAME, 0.4 * cm, 0.4 * cm)
    im_fb = Image(ASSETS_FACEBOOK_FILENAME, 0.4 * cm, 0.4 * cm)
    im_t = Image(ASSETS_TWITTER_FILENAME, 0.4 * cm, 0.4 * cm)
    im_logo = Image(ASSETS_LOGO_FILENAME, 3.472 * cm, 1 * cm)

    if user.room:
        shortinfo = Paragraph('{dorm}<br/>{name}<br/>{level}/{room}'.format(
            dorm=str(user.room.building.short_name),
            name=user.name,
            level=str(user.room.level),
            room=str(user.room.number)
        ), style['RightText'])
    else:
        shortinfo = Paragraph('{name}'.format(
            name=user.name
        ), style['RightText'])

    data = [
        [im_web, 'https://agdsn.de', im_t, '/ag_dsn'],
        [im_email, 'support@agdsn.de', im_fb, '/DresdnerStudentenNetz']
    ]
    social = Table(data, colWidths=[0.5 * cm, 3.5 * cm, 0.5 * cm],
                   rowHeights=[0.5 * cm] * 2)

    data = [[im_logo, social, shortinfo]]
    t = Table(data, colWidths=[3.972 * cm, 9.5 * cm, 4 * cm],
              style=[
                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ])
    story.append(t)
    ######################

    story.append(HRFlowable(width="100%",
                            thickness=1,
                            color=black,
                            spaceBefore=0.0 * cm,
                            spaceAfter=0.8 * cm))

    story.append(
        Paragraph('Hello {},'
                  .format(user.name),
                  style['BodyText']))

    story.append(
        Paragraph("We've been working on provisioning Wi-Fi for all members lately. "
                  "To gain experience with operating an Wi-Fi in larger scale, "
                  "we are putting it into test operation at the Gret-Palucca-Strasse dormitory. "
                  "With this test operation we want to find out, among other things, "
                  "how good the coverage of the signal is in different parts of the building and "
                  "whether the underlying services for managing the networks and "
                  "the conversion to the public IP address work. ",
                  style['BodyText']))

    story.append(
        Paragraph(
            'You can find instructions to connect, further information and data protection notices at: '
            'https://agdsn.de/sipa/pages/service/wlan-test',
            style['BodyText'])
    )

    story.append(
        Paragraph(
            'We would really like, if you try our wifi. '
            'If you have any questions, feedback or problems, please come to our office or write to us.',
            style['BodyText'])
    )

    data = [
        ['SSID:', 'agdsn-gps-test'],
        ['Outer authentication:', 'TTLS'],
        ['Inner authentication:', 'PAP'],
        ['CA certificate:', 'Use system certificate (when unavailable download\nfrom our website)'],
        ['Domain:', 'radius.agdsn.de'],
        ['Anonymous identity:', 'anonymous@agdsn.de'],
        ['Username:', user.login],
        ['Password:', plain_password]
    ]
    credential_table = Table(data, colWidths=[4 * cm, 4 * cm],
                          style=[
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                          ])

    qr_size = 4 * cm
    qr_code = qr.QrCodeWidget('https://agdsn.de/sipa/pages/service/wlan-test')
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    qrcode = Drawing(qr_size, qr_size,
                       transform=[qr_size / width, 0, 0, qr_size / height, 0,
                                  0])
    qrcode.add(qr_code)

    data = [[credential_table, qrcode]]
    t = Table(data, colWidths=[13 * cm, 4 * cm],
              style=[
                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
              ])
    story.append(t)

    story.append(Paragraph('Best regards,', style['BodyText']))
    story.append(Paragraph('Your AG DSN', style['BodyText']))

    s = Spacer(width=1 * cm, height=8.8 * cm)
    story.append(s)

    story.append(HRFlowable(width="100%",
                            thickness=3,
                            color=black,
                            spaceBefore=0.4 * cm,
                            spaceAfter=0.4 * cm))
    # offices
    im_web = Image(ASSETS_WEB_FILENAME, 0.4 * cm, 0.4 * cm)
    im_house = Image(ASSETS_HOUSE_FILENAME, 0.4 * cm, 0.4 * cm)
    im_email = Image(ASSETS_EMAIL_FILENAME, 0.4 * cm, 0.4 * cm)
    im_fb = Image(ASSETS_FACEBOOK_FILENAME, 0.4 * cm, 0.4 * cm)
    im_t = Image(ASSETS_TWITTER_FILENAME, 0.4 * cm, 0.4 * cm)
    data = [
        ['', im_house, 'Wundtstraße 5', im_house, 'Hochschulstr. 50', im_house,
         'Borsbergstr. 34'],
        ['', '', 'Doorbell 0100', '', 'Ground floor', '', '7th floor'],
        ['', '', '01217 Dresden', '', '01069 Dresden', '', '01309 Dresden'],
        ['', '', '', '', '', '', ''],
        ['Office hours:', '', 'Mon, 7pm - 8pm', '', 'Mon, 7pm - 7.30pm', '',
         'Mon, 8pm - 9pm'],
        ['', '', 'Thu, 7pm - 8pm', '', 'Thu, 7pm - 7.30pm', '',
         'Thu, 8pm - 9pm']
    ]

    rowHeight = 0.4 * cm
    t = Table(data, colWidths=[2.5 * cm, 0.5 * cm, 3.5 * cm, 0.5 * cm, 3.5 * cm,
                               0.5 * cm, 3.5 * cm],
              rowHeights=[rowHeight, rowHeight, rowHeight, rowHeight, rowHeight,
                          rowHeight],
              hAlign='CENTER'
              )
    story.append(t)

    story.append(
        Paragraph(
            '<i>Generated on {date}</i>'.format(
                date=datetime.date.today(),
            ),
            ParagraphStyle(name='SmallRightText',
                           parent=style['Normal'],
                           alignment=TA_RIGHT,
                           fontSize=8,
                           spaceBefore=15))
    )

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
                                  spaceBefore=7))

    stylesheet.add(ParagraphStyle(name='RightText',
                                  parent=stylesheet['Normal'],
                                  alignment=TA_RIGHT,
                                  spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='JustifyText',
                                 parent=stylesheet['Normal'],
                                 alignment=TA_JUSTIFY,
                                 spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='CenterText',
                                  parent=stylesheet['Normal'],
                                  alignment=TA_CENTER,
                                  spaceBefore=14))

    stylesheet.add(ParagraphStyle(name='Bold',
                                  parent=stylesheet['BodyText'],
                                  fontName="Helvetica-Bold"))

    return stylesheet

def generate_epc_qr_code(bank: BankAccount, recipient, amount, purpose):
    # generate content for epc-qr-code (also known as giro-code)
    EPC_FORMAT = \
        "BCD\n001\n1\nSCT\n{bic}\n{recipient}\n{iban}\nEUR{amount}\n\n\n{purpose}\n\n"

    return EPC_FORMAT.format(
        bic=bank.bic,
        recipient=recipient,
        iban=bank.iban,
        amount=amount,
	purpose=purpose)
