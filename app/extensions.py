from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import flask_praetorian

db = SQLAlchemy()
ma = Marshmallow()
guard = flask_praetorian.Praetorian()