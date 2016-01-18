# -*- coding: utf-8 -*-

"""
Annotation domain model classes.

Classes to represent objects managed by the Annotations API.
"""

from __future__ import unicode_literals

import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.ext.hybrid import hybrid_property

from h.api import uri
from h.api.db import Base
from h.api.db import types


class Timestamps(object):
    created = sa.Column(sa.DateTime,
                        default=datetime.datetime.utcnow,
                        server_default=sa.func.now(),
                        nullable=False)
    updated = sa.Column(sa.DateTime,
                        server_default=sa.func.now(),
                        default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow,
                        nullable=False)


class Annotation(Base, Timestamps):
    __tablename__ = 'annotation'
    __table_args__ = (
        sa.Index('ix_annotation_tags', 'tags', postgresql_using='gin'),
    )

    id = sa.Column(types.URLSafeUUID,
                   server_default=sa.func.uuid_generate_v1mc(),
                   primary_key=True)

    userid = sa.Column(sa.UnicodeText,
                       nullable=False,
                       index=True)
    groupid = sa.Column(sa.UnicodeText,
                        default='__world__',
                        server_default='__world__',
                        nullable=False,
                        index=True)

    text = sa.Column(sa.UnicodeText)
    tags = sa.Column(pg.ARRAY(sa.UnicodeText, zero_indexes=True),
                     index=True)

    shared = sa.Column(sa.Boolean,
                       nullable=False,
                       default=False,
                       server_default=sa.sql.expression.false())

    targets = sa.Column(pg.JSONB,
                        default=list,
                        server_default=sa.func.jsonb('[]'))

    references = sa.Column(pg.ARRAY(types.URLSafeUUID),
                           default=list,
                           server_default=sa.text('ARRAY[]::uuid[]'))

    extra = sa.Column(pg.JSONB, nullable=True)

    def __repr__(self):
        return '<Annotation %s>' % self.id


class Document(Base, Timestamps):
    __tablename__ = 'document'

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    uris = sa.orm.relationship('DocumentURI', backref='document')
    meta = sa.orm.relationship('DocumentMeta', backref='document')

    def __repr__(self):
        return '<Document %s>' % self.id


class DocumentURI(Base, Timestamps):
    __tablename__ = 'document_uri'

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    _claimant = sa.Column('claimant',
                          sa.UnicodeText,
                          nullable=False)
    _claimant_normalized = sa.Column('claimant_normalized',
                                     sa.UnicodeText,
                                     nullable=False)

    _uri = sa.Column('uri',
                     sa.UnicodeText,
                     nullable=False)
    _uri_normalized = sa.Column('uri_normalized',
                                sa.UnicodeText,
                                nullable=False)

    type = sa.Column(sa.UnicodeText)
    canonical = sa.Column(sa.Boolean,
                          nullable=False,
                          default=False,
                          server_default=sa.sql.expression.false())

    document_id = sa.Column(sa.Integer, sa.ForeignKey('document.id'))

    @hybrid_property
    def claimant(self):
        return self._claimant

    @claimant.setter
    def claimant(self, value):
        self._claimant = value
        self._claimant_normalized = uri.normalize(value)

    @hybrid_property
    def claimant_normalized(self):
        return self._claimant_normalized

    @hybrid_property
    def uri(self):
        return self._uri

    @uri.setter
    def uri(self, value):
        self._uri = value
        self._uri_normalized = uri.normalize(value)

    @hybrid_property
    def uri_normalized(self):
        return self._uri_normalized

    def __repr__(self):
        return '<DocumentURI %s>' % self.id


class DocumentMeta(Base, Timestamps):
    __tablename__ = 'document_meta'

    id = sa.Column(sa.Integer, autoincrement=True, primary_key=True)

    _claimant = sa.Column('claimant',
                          sa.UnicodeText,
                          nullable=False)
    _claimant_normalized = sa.Column('claimant_normalized',
                                     sa.UnicodeText,
                                     nullable=False)

    type = sa.Column(sa.UnicodeText, nullable=False)
    value = sa.Column(sa.UnicodeText, nullable=False)

    document_id = sa.Column(sa.Integer, sa.ForeignKey('document.id'))

    @hybrid_property
    def claimant(self):
        return self._claimant

    @claimant.setter
    def claimant(self, value):
        self._claimant = value
        self._claimant_normalized = uri.normalize(value)

    @hybrid_property
    def claimant_normalized(self):
        return self._claimant_normalized

    def __repr__(self):
        return '<DocumentMeta %s>' % self.id
