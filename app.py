from flask import Flask, render_template, request, redirect, session
from database import DatabaseManager
import os


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")
db = DatabaseManager()

@app.route('/', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.connecter(email, password)
        if user:
            session['user_id'] = user['id_user']
            session['user_pseudo'] = user['pseudo']
            session['user_is_admin'] = user['is_admin']
            return redirect('/accueil')
        else:
            return render_template('connexion.html', erreur='Email ou mot de passe incorrect')
    return render_template('connexion.html')

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        pseudo = request.form['pseudo']
        if db.inscrire(email, password, pseudo):
            user = db.connecter(email, password)
            if user:
                session['user_id'] = user['id_user']
                session['user_pseudo'] = user['pseudo']
                session['user_is_admin'] = user['is_admin']
                return redirect('/accueil')
            else:
                return redirect('/connexion')
        else:
            return render_template('inscription.html', erreur='Email déjà utilisé')
    return render_template('inscription.html')

@app.route('/accueil')
def accueil():
    return render_template('accueil.html')

@app.route('/discussion')
def discussion():
    return render_template('discussion.html')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')