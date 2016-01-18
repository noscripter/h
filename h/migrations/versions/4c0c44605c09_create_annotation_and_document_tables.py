"""Create annotation and document tables

Revision ID: 4c0c44605c09
Revises: 4886d7a14074
Create Date: 2016-01-20 12:58:16.249481

"""

# revision identifiers, used by Alembic.
revision = '4c0c44605c09'
down_revision = '4886d7a14074'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


from h.api.db import types


def upgrade():
    op.create_table('annotation',
        sa.Column('id',
                  types.URLSafeUUID,
                  server_default=sa.func.uuid_generate_v1mc(),
                  primary_key=True),
        sa.Column('created', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('userid', sa.UnicodeText(), nullable=False),
        sa.Column('groupid', sa.UnicodeText(), server_default=u'__world__', nullable=False),
        sa.Column('text', sa.UnicodeText(), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.UnicodeText, zero_indexes=True), nullable=True),
        sa.Column('shared', sa.Boolean, server_default=sa.sql.expression.false(), nullable=False),
        sa.Column('targets', postgresql.JSONB, server_default=sa.func.jsonb('[]'), nullable=True),
        sa.Column('references',
                  postgresql.ARRAY(types.URLSafeUUID),
                  server_default=sa.text('ARRAY[]::uuid[]'),
                  nullable=True),
        sa.Column('extra', postgresql.JSONB, nullable=True),
    )
    op.create_index(op.f('ix__annotation_groupid'), 'annotation', ['groupid'], unique=False)
    op.create_index(op.f('ix__annotation_tags'), 'annotation', ['tags'], postgresql_using='gin', unique=False)
    op.create_index(op.f('ix__annotation_userid'), 'annotation', ['userid'], unique=False)

    op.create_table('document',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    op.create_table('document_meta',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('claimant', sa.UnicodeText, nullable=False),
        sa.Column('claimant_normalized', sa.UnicodeText, nullable=False),
        sa.Column('type', sa.UnicodeText, nullable=False),
        sa.Column('value', sa.UnicodeText, nullable=False),
        sa.Column('document_id', sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(['document_id'], [u'document.id']),
    )

    op.create_table('document_uri',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('created', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('updated', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('claimant', sa.UnicodeText, nullable=False),
        sa.Column('claimant_normalized', sa.UnicodeText, nullable=False),
        sa.Column('uri', sa.UnicodeText, nullable=False),
        sa.Column('uri_normalized', sa.UnicodeText, nullable=False),
        sa.Column('type', sa.UnicodeText, nullable=True),
        sa.Column('canonical', sa.Boolean(), server_default=sa.sql.expression.false(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], [u'document.id']),
    )


def downgrade():
    op.drop_table('document_uri')
    op.drop_table('document_meta')
    op.drop_table('document')
    op.drop_index(op.f('ix__annotation_userid'), table_name='annotation')
    op.drop_index(op.f('ix__annotation_tags'), table_name='annotation')
    op.drop_index(op.f('ix__annotation_groupid'), table_name='annotation')
    op.drop_table('annotation')
