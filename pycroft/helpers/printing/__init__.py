# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import cairo
import pango
import pangocairo
import poppler

from json import load as json_load
from os.path import dirname, join, realpath
from StringIO import StringIO
from urllib import pathname2url
from urlparse import urljoin

ASSETS_DIRECTORY = join(dirname(__file__), 'assets')
ASSETS_PDF_FILENAME = join(ASSETS_DIRECTORY, 'user_sheet.pdf')
ASSETS_POS_FILENAME = join(ASSETS_DIRECTORY, 'user_sheet_position.json')

# Cairo needs some weird URL for opening the file.
def path2url(path):
    return urljoin('file:', pathname2url(path))

def cairo_surface_from_template(surface, template_filename):
    uri = path2url(realpath(template_filename))
    document = poppler.document_new_from_file(uri, None)
    page = document.get_page(0)
    w, h = page.get_size()
    surface.set_size(w, h)
    cx = cairo.Context(surface)
    page.render_for_printing(cx)

def generate_user_sheet(user, plain_password):
    macs = []
    for user_host in user.user_hosts:
        for ip in user_host.ips:
            macs.append(ip.interface.mac)

    data = {
        'name': user.name,
        'login': user.login,
        'password': plain_password,
        'mac': ', '.join(macs),
        'dormitory': '{} {}'.format(user.room.building.street, user.room.building.number),
        'level': str(user.room.level),
        'room': str(user.room.number),
    }

    buf = StringIO()
    surface = cairo.PDFSurface(buf, 0, 0)
    cairo_surface_from_template(surface, ASSETS_PDF_FILENAME)
    with open(ASSETS_POS_FILENAME, 'r') as f:
        positions = json_load(f)

    font = pango.FontDescription()
    font.set_family('DejaVu Sans')
    font.set_size(8 * 1024)

    cx = pangocairo.CairoContext(cairo.Context(surface))
    for entry, position in positions.items():
        cx.save()
        layout = cx.create_layout()
        layout.set_text(data[entry])
        layout.set_font_description(font)
        layout.set_single_paragraph_mode(True)
        cx.move_to(*position)
        cx.show_layout(layout)
        cx.restore()

    surface.show_page()
    surface.finish()
    return buf.getvalue()
