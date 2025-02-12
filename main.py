from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime
import sqlite3

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///drive.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

# Event and Tag Models
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    drive_id = db.Column(db.String(50), db.ForeignKey('drive.id'), nullable=False)
    tags = db.relationship('Tag', secondary='event_tag', backref='events')

# Association Table for Many-to-Many Relationship between Event and Tag
event_tag = db.Table('event_tag',
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

# Drive Model with a list of events
class Drive(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    driver = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    finas_id = db.Column(db.String(50), nullable=True)  # Added finas_id field
    date_created = db.Column(db.DateTime, default=datetime.utcnow) 
    events = db.relationship('Event', backref='drive', lazy=True)

# Authentication Decorator
def authenticate(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# API Class
class DriveAPI:
    def get(self, drive_id=None, finas_id=None, date=None):
        query = Drive.query

        if drive_id:
            query = query.filter_by(id=drive_id)
        if finas_id:
            query = query.filter_by(finas_id=finas_id)
        if date:
            query = query.filter(db.func.date(Drive.date_created) == date)

        drives = query.all()
        return [{'id': drive.id, 'name': drive.name, 'finas_id': drive.finas_id, 'date_created': drive.date_created, 'events': [{'id': e.id, 'comment': e.comment, 'time': e.time, 'tags': [t.name for t in e.tags]} for e in drive.events]} for drive in drives]

    def post(self, name, finas_id, driver=''):
        try:
            # Input validation
            if not finas_id or not name:
                return jsonify({'error': 'finas_id and name are required fields'}), 400

            # Create new Drive entry
            new_drive = Drive(driver=driver, name=name, finas_id=finas_id)

            # Add to database
            db.session.add(new_drive)
            db.session.commit()

            # Return success response
            return new_drive

        except Exception as e:
            return jsonify({'error': str(e)}), 500

    def put(self, drive_id, name, finas_id=None):
        drive = Drive.query.get(drive_id)
        if drive:
            drive.name = name
            drive.finas_id = finas_id
            db.session.commit()
            return {'message': 'Drive updated'}
        return {'message': 'Drive not found'}, 404

    def delete(self, drive_id):
        drive = Drive.query.get(drive_id)
        if drive:
            db.session.delete(drive)
            db.session.commit()
            return {'message': 'Drive deleted'}
        return {'message': 'Drive not found'}, 404

    def add_event(self, drive_id, comment, tags):
        new_event = Event(comment=comment, drive_id=drive_id)
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag:
                new_event.tags.append(tag)
        db.session.add(new_event)
        db.session.commit()
        return new_event

    def update_event(self, event_id, comment, tags):
        event = Event.query.get(event_id)
        if event:
            event.comment = comment
            event.tags = []  # Clear existing tags
            for tag_name in tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag:
                    event.tags.append(tag)
            db.session.commit()
            return {'message': 'Event updated'}
        return {'message': 'Event not found'}, 404

    def delete_event(self, event_id):
        event = Event.query.get(event_id)
        if event:
            db.session.delete(event)
            db.session.commit()
            return {'message': 'Event deleted'}
        return {'message': 'Event not found'}, 404

drive_api = DriveAPI()

@app.route('/')
# @authenticate
def index():
    return render_template('index.html')

@app.route('/drives', methods=['GET'])
# @authenticate
def view_drives():
    drives = drive_api.get()
    return render_template('view_drives.html', drives=drives)

@app.route('/add_drive', methods=['GET', 'POST'])
# @authenticate
def add_drive():
    if request.method == 'POST':
        driver = request.form['driver']
        name = request.form['name']
        finas_id = request.form.get('finas_id')
        new_drive = drive_api.post(name, finas_id, driver)
        return redirect(url_for('edit_drive', drive_id=new_drive.id))
    return render_template('add_drive.html')

@app.route('/edit/<drive_id>', methods=['GET', 'POST'])
# @authenticate
def edit_drive(drive_id):
    drive = Drive.query.get(drive_id)
    if request.method == 'POST':
        if 'name' in request.form:
            finas_id = request.form.get('finas_id')
            drive_api.put(drive_id, request.form['name'], finas_id)
        elif 'comment' in request.form:
            comment = request.form.get('comment', '')
            tags = request.form.getlist('tags')
            drive_api.add_event(drive_id, comment, tags)
        return redirect(url_for('edit_drive', drive_id=drive_id))
    return render_template('edit.html', drive=drive)

@app.route('/edit_event/<event_id>', methods=['GET', 'POST'])
# @authenticate
def edit_event(event_id):
    event = Event.query.get(event_id)
    if request.method == 'POST':
        comment = request.form.get('comment', '')
        tags = request.form.getlist('tags')
        drive_api.update_event(event_id, comment, tags)
        return redirect(url_for('edit_drive', drive_id=event.drive_id))
    return render_template('edit_event.html', event=event)

@app.route('/delete_event/<event_id>', methods=['POST'])
@authenticate
def delete_event(event_id):
    event = Event.query.get(event_id)
    if event:
        drive_id = event.drive_id
        drive_api.delete_event(event_id)
        return redirect(url_for('edit_drive', drive_id=drive_id))
    return jsonify({'message': 'Event not found'}), 404

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
