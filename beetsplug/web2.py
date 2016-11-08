# -*- coding: utf-8 -*-
# Copyright 2013, Marcel Hellkamp.
# Copyright 2016, Adrian Sampson.
# Copyright 2016, Martin Zimmermann.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

import os
import re
import time

from beets import library, ui
from beets.plugins import BeetsPlugin

from bottle import Bottle, HTTPResponse, HTTPError
from bottle import request, parse_date, parse_range_header, _file_iter_range


def _get_unique_table_field_values(lib, model, field, sort_field):
    """retrieve all unique values belonging to a key from a model"""
    if field not in model.all_keys() or sort_field not in model.all_keys():
        raise KeyError
    with lib.transaction() as tx:
        rows = tx.query('SELECT DISTINCT "{0}" FROM "{1}" ORDER BY "{2}"'
                        .format(field, model._table, sort_field))
    return [row[0] for row in rows]


def to_dict(obj):
    if isinstance(obj, library.Item):
        return {k: getattr(obj, k) for k in [
            'id', 'album_id', 'title', 'artist', 'composer', 'genre', 'track',
            'original_year', 'original_month', 'original_day',
            'year', 'month', 'day', 'length', 'bitrate', 'disc'
        ]}
    elif isinstance(obj, library.Album):
        return {k: getattr(obj, k) for k in [
            'id', 'album', 'albumartist', 'disctotal', 'genre',
            'original_year', 'original_month', 'original_day',
            'year', 'month', 'day'
        ]}
    else:
        return {}


def ids_list_filter(config):
    delimiter = config or ','
    regexp = r'\d+(%s\d+)*' % re.escape(delimiter)

    def to_python(match):
        try:
            return map(int, match.split(delimiter))
        except ValueError:
            return []

    def to_url(ids):
        return ','.join(ids)

    return regexp, to_python, to_url


class Web2(object):

    def __init__(self, lib):
        self.lib = lib

    def get_items(self, ids=None):
        if ids is None:
            return {'items': [
                to_dict(item) for item in self.lib.items()
            ]}
        else:
            items = [to_dict(item) for item in map(self.lib.get_item, ids) if item]
            if len(items) == 1:
                return items[0]
            else:
                return {'items': items}

    def get_item_query(self, query):
        return {'results': [
            to_dict(item) for item in self.lib.items(query.split('/'))
        ]}

    def get_item_unique_field_values(self, key):
        sort_key = request.query.sort_key or key
        try:
            return {'values': _get_unique_table_field_values(
                self.lib, library.Item, key, sort_key)}
        except KeyError:
            return HTTPError(404)

    def get_albums(self, ids=None):
        if ids is None:
            return {'albums': [
                to_dict(album) for album in self.lib.albums()
            ]}
        else:
            albums = [to_dict(album) for album in map(self.lib.get_album, ids) if album]
            if len(albums) == 1:
                return albums[0]
            else:
                return {'albums': albums}

    def get_album_query(self, query):
        return {'results': [
            to_dict(album) for album in self.lib.albums(query.split('/'))
        ]}

    def get_album_unique_field_values(self, key):
        sort_key = request.query.sort_key or key
        try:
            return {'values': _get_unique_table_field_values(
                self.lib, library.Album, key, sort_key)}
        except KeyError:
            return HTTPError(404)

    def get_item_file(self, id):
        item = self.lib.get_item(id)
        if item is None:
            return HTTPError(404, 'File does not exist.')

        if not os.access(item.path, os.R_OK):
            return HTTPError(403, 'You do not have permission to access this file.')

        stats = os.stat(item.path)
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Length': stats.st_size,
            'Last-Modified': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(stats.st_mtime)),
            'Date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        }

        ims = request.environ.get('HTTP_IF_MODIFIED_SINCE')
        if ims:
            ims = parse_date(ims.split(";")[0].strip())
        if ims is not None and ims >= int(stats.st_mtime):
            return HTTPResponse(status=304, **headers)

        body = '' if request.method == 'HEAD' else open(item.path, 'rb')

        headers["Accept-Ranges"] = "bytes"
        range_header = request.environ.get('HTTP_RANGE')
        if range_header:
            ranges = list(parse_range_header(range_header, stats.st_size))
            if not ranges:
                return HTTPError(416, "Requested Range Not Satisfiable")

            offset, end = ranges[0]
            headers["Content-Range"] = "bytes %d-%d/%d" % (offset, end - 1, stats.st_size)
            headers["Content-Length"] = str(end - offset)
            if body:
                body = _file_iter_range(body, offset, end - offset)

            return HTTPResponse(body, status=206, **headers)

        return HTTPResponse(body, **headers)


def make_app(lib):
    web2 = Web2(lib)

    app = Bottle()
    app.router.add_filter('list', ids_list_filter)

    app.route('/item/', 'GET', web2.get_items)
    app.route('/item/query/', 'GET', web2.get_items)
    app.route('/item/<ids:list>', 'GET', web2.get_items)
    app.route('/item/values/<key:path>', 'GET', web2.get_item_unique_field_values)
    app.route('/item/query/<query:path>', 'GET', web2.get_item_query)
    app.route('/item/<id:int>/file', 'GET', web2.get_item_file)

    app.route('/album/', 'GET', web2.get_albums)
    app.route('/album/query/', 'GET', web2.get_albums)
    app.route('/album/<ids:list>', 'GET', web2.get_albums)
    app.route('/album/values/<key:path>', 'GET', web2.get_album_unique_field_values)
    app.route('/album/query/<query:path>', 'GET', web2.get_album_query)

    return app


class WebPlugin(BeetsPlugin):
    def __init__(self):
        super(WebPlugin, self).__init__()
        self.config.add({
            'host': '127.0.0.1',
            'port': 8337,
            'server': 'wsgiref'
        })

    def commands(self):
        cmd = ui.Subcommand('web2', help='start a Web2 interface')
        cmd.parser.add_option('-d', '--debug', action='store_true',
                              default=False, help='debug mode')

        def func(lib, opts, args):
            args = ui.decargs(args)
            if args:
                self.config['host'] = args.pop(0)
            if args:
                self.config['port'] = int(args.pop(0))
            if args:
                self.config['server'] = args.pop(0)

            host = self.config['host'].as_str()
            port = self.config['port'].get(int)
            server = self.config['server'].as_str()

            app = make_app(lib)
            app.run(host=host, port=port, server=server, debug=opts.debug)

        cmd.func = func
        return [cmd]
