from web import make_app
from pycroft.lib import config

if __name__ == "__main__":
    app = make_app()
    app.debug = True

    app.config['MAX_CONTENT_LENGTH'] = \
        int(config.get("file_upload")["max_file_size"])
    app.config['UPLOAD_FOLDER'] = config.get("file_upload")["temp_dir"]

    app.run(debug=True)