from flask import Flask
from . import template_filters # Import the new filters file

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a-very-secret-key-that-should-be-changed'

    # Register the custom filter
    app.jinja_env.filters['format_unit'] = template_filters.format_unit

    with app.app_context():
        from . import routes
        app.register_blueprint(routes.main_bp)

    return app
