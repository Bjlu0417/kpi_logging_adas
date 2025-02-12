from flask import Flask, render_template, redirect, url_for, request
app = Flask(__name__)


class Session():
    def __init__(self, finas):
        self.finas = "000-0000"
    


@app.route('/')
def show_landing_page():
    return render_template("index.html")

@app.route('/new', methods = ['POST'])
def add_new_session():
    new_session = request.json
    return render_template("new.html")




if __name__ == "__main__":
    app.run(debug=True)