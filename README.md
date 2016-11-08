# beets-web2

Alternate web API using the Bottle web framework to support HTTP Range
requests (a technique to support "seeking" with Gstreamer). MusicBrainz
metadata has been removed to reduce payload size.

## Installation

    $ pip install beets-web2 waitress

## Configuration

* hostname: web's hostname
* port: web's port
* server: override WSGI server (default: auto)
* username: username (enable auth)
* password: password (enable auth)

## Deployment

X-Script-Name is supported.
