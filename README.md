# beets-web2

Alternate web API using the Bottle web framework to support HTTP Range
requests (a technique to support "seeking" with Gstreamer). MusicBrainz
metadata has been removed to reduce payload size.

## Installation

    $ pip install beets-web2 waitress

## Configuration

    The plugin accepts the same options as web.
