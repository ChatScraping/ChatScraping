from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///conversations.rev_2024-06-27.db'

app.config['SQLALCHEMY_BINDS'] = {
    'documents': 'sqlite:///documents.rev_2024-06-27.db'
}

db = SQLAlchemy(app)

class Text(db.Model):
    __bind_key__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False, unique=True)
    url_version_id = db.Column(db.Integer, db.ForeignKey('url_version.id'))
    origin = db.Column(db.String(1024), nullable=False, default="ChatScraping version 2024-06-27")
    rating = db.Column(db.Integer, nullable=True)
    __table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 100', name='check_rating_range'),
    )
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

class URL(db.Model):
    __bind_key__ = 'documents'
    __tablename__ = 'url'
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), nullable=False, unique=True)
    page_title = db.Column(db.String(255), nullable=True)
    body =  db.Column(db.String(1024), nullable=True)
    origin = db.Column(db.String(1024), nullable=False, default="ChatScraping version 2024-06-27")
    rating = db.Column(db.Integer, nullable=True)
    __table_args__ = (
        CheckConstraint('rating >= 0 AND rating <= 100', name='check_rating_range'),
    )
    is_saved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    versions = db.relationship('URL_version', backref='url', lazy=True)

class URL_version(db.Model):
    __bind_key__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, db.ForeignKey('url.id'))
    all_readable_text = db.Column(db.Text, nullable=True)
    all_readable_text_edited = db.Column(db.Text, nullable=True)
    html_file_path = db.Column(db.Text)
    pdf_file_path = db.Column(db.Text)
    are_texts_saved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    texts = db.relationship('Text', backref='url_version', lazy=True)

class Tag(db.Model):
    __bind_key__ = 'documents'
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

tags_texts = db.Table('tags_texts',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('text_id', db.Integer, db.ForeignKey('text.id'), primary_key=True),
    bind_key = "documents",
)
tags = db.relationship('Tag', secondary=tags_texts, backref='texts', lazy=True)

tags_urls = db.Table('tags_urls',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('url_id', db.Integer, db.ForeignKey('url.id'), primary_key=True),
    bind_key = "documents",
)
URL.tags = db.relationship('Tag', secondary=tags_urls, backref='urls', lazy=True)
    
class Comment(db.Model):
    __bind_key__ = "documents"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

comments_urls = db.Table('comments_urls',
    db.Column('comment_id', db.Integer, db.ForeignKey('comment.id'), primary_key=True),
    db.Column('url_id', db.Integer, db.ForeignKey('url.id'), primary_key=True),
    bind_key = "documents",
)
URL.comments = db.relationship('Comment', secondary=comments_urls, backref='urls', lazy=True)
