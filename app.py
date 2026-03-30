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

@app.route('/deconnexion')
def deconnexion():
    session.clear()
    return redirect('/')

@app.route('/accueil')
def accueil():
    discussions = db.recuperer_discussions(id_user=session['user_id'])
    users = db.recuperer_utilisateurs()
    return render_template('accueil.html', discussions=discussions, users=users)

@app.route('/discussion/<int:id_user>', methods=['GET', 'POST'])
def discussion(id_user):
    if request.method == 'POST':
        content = request.form['content']
        db.creer_message(content, session['user_id'], id_user)
    messages = db.recuperer_messages(session['user_id'], id_user)
    user = db.recuperer_utilisateur(id_user)
    return render_template('discussion.html', messages=messages, user=user, id_user=id_user, session=session)

@app.route('/mon_compte')
def mon_compte():
    return render_template('mon_compte.html')

@app.route('/supprimer_message/<int:id_message>', methods=['POST'])
def supprimer_message(id_message):
    if 'user_id' not in session:
        return redirect('/')
    id_user = request.form.get('id_user')
    if id_user:
        db.supprimer_message(id_message, session['user_id'])
        return redirect(f'/discussion/{id_user}')
    return redirect('/accueil')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')