from flask import Flask, jsonify, render_template


def make_app(state):
    app = Flask(__name__)

    @app.get('/')
    def index():
        return render_template('index.html')

    @app.get('/api/status')
    def status():
        response = jsonify(state.snapshot())
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/events')
    def events():
        return jsonify(state.snapshot()['events'])

    return app
