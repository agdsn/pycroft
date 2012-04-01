from web import make_app

if __name__ == "__main__":
    app = make_app()
    app.run(debug=True)