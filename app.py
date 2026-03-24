from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def connexion():
    return render_template('connexion.html')

@app.route('/inscription')
def inscription():
    return render_template('inscription.html')

@app.route('/accueil')
def accueil():
    return render_template('accueil.html')

@app.route('/discussion')
def discussion():
    return render_template('discussion.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')