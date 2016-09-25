from flask import Flask
from api import api

app = Flask(__name__, static_url_path='')
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def fff():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.debug = True
    app.run()


