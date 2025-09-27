#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask Tutorial - Version 1 (Einfache Version für Schüler)
==========================================================

Diese Version zeigt die Grundlagen von Flask:
- Einfache Routen und Templates
- Benutzerverwaltung (Registration/Login)
- Datenbank mit SQLAlchemy
- Einfache Posts erstellen und anzeigen
- Grundlegendes CSS-Styling

Ideal zum Lernen der Flask-Grundlagen!
"""

import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Flask App erstellen
app = Flask(__name__)

# Konfiguration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///simple_blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Datenbank initialisieren
db = SQLAlchemy(app)

# =============================================================================
# DATENBANK MODELLE
# =============================================================================

class User(db.Model):
    """Benutzer-Modell für die Datenbank"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)

    def set_password(self, password):
        """Passwort verschlüsseln und speichern"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Passwort prüfen"""
        return check_password_hash(self.password_hash, password)

class Post(db.Model):
    """Post-Modell für Blogbeiträge"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# =============================================================================
# FORMULARE
# =============================================================================

class RegistrationForm(FlaskForm):
    """Registrierungsformular"""
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Registrieren')

class LoginForm(FlaskForm):
    """Anmeldeformular"""
    username = StringField('Benutzername', validators=[DataRequired()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    submit = SubmitField('Anmelden')

class PostForm(FlaskForm):
    """Formular für neue Posts"""
    title = StringField('Titel', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('Inhalt', validators=[DataRequired()])
    submit = SubmitField('Post veröffentlichen')

# =============================================================================
# ROUTEN (URLs)
# =============================================================================

@app.route('/')
def home():
    """Startseite mit allen Posts"""
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('home.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registrierung für neue Benutzer"""
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Prüfen ob Benutzername oder E-Mail bereits existiert
        existing_user = User.query.filter_by(username=form.username.data).first()
        existing_email = User.query.filter_by(email=form.email.data).first()
        
        if existing_user:
            flash('Benutzername bereits vergeben!', 'danger')
            return render_template('register.html', form=form)
        
        if existing_email:
            flash('E-Mail bereits registriert!', 'danger')
            return render_template('register.html', form=form)
        
        # Neuen Benutzer erstellen
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registrierung erfolgreich!', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Anmeldung für Benutzer"""
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Anmeldung erfolgreich!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Ungültiger Benutzername oder Passwort!', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    """Benutzer abmelden"""
    session.clear()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('home'))

@app.route('/new_post', methods=['GET', 'POST'])
def new_post():
    """Neuen Post erstellen"""
    # Prüfen ob Benutzer angemeldet ist
    if 'user_id' not in session:
        flash('Bitte zuerst anmelden!', 'warning')
        return redirect(url_for('login'))
    
    form = PostForm()
    
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            user_id=session['user_id']
        )
        
        db.session.add(post)
        db.session.commit()
        
        flash('Post wurde veröffentlicht!', 'success')
        return redirect(url_for('home'))
    
    return render_template('new_post.html', form=form)

@app.route('/user/<username>')
def user_profile(username):
    """Benutzerprofil anzeigen"""
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(author=user).order_by(Post.date_posted.desc()).all()
    return render_template('user_profile.html', user=user, posts=posts)

# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

@app.context_processor
def inject_user():
    """Stellt aktuelle Benutzerinformationen in allen Templates zur Verfügung"""
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
        return dict(current_user=current_user)
    return dict(current_user=None)

# =============================================================================
# APP STARTEN
# =============================================================================

if __name__ == '__main__':
    # Datenbank-Tabellen erstellen (falls sie nicht existieren)
    with app.app_context():
        db.create_all()
        print("✅ Datenbank initialisiert!")
    
    print("🚀 Flask App gestartet!")
    print("📝 Öffne http://127.0.0.1:5000 in deinem Browser")
    print("📚 Dies ist die einfache Version für Schüler")
    
    # App im Debug-Modus starten
    app.run(debug=True)