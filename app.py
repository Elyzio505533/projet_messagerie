from flask import Flask, render_template, request, redirect, session
from database import DatabaseManager
import os


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev")
UPLOAD_FOLDER = 'static/avatars'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = DatabaseManager()

# Rendre session disponible dans tous les templates
@app.context_processor
def inject_session():
    return {'session': session}

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
    
    # Convertir les Row en dictionnaires mutables et ajouter le nombre de messages non lus
    discussions_with_unread = []
    for discussion in discussions:
        discussion_dict = dict(discussion)
        unread_count = db.count_unread_messages(session['user_id'], discussion['id_user'])
        discussion_dict['unread_count'] = unread_count
        discussions_with_unread.append(discussion_dict)
    
    return render_template('accueil.html', discussions=discussions_with_unread, users=users)

@app.route('/discussion/<int:id_user>', methods=['GET', 'POST'])
def discussion(id_user):
    if request.method == 'POST':
        content = request.form['content']
        db.creer_message(content, session['user_id'], id_user)
    
    messages = db.recuperer_messages(session['user_id'], id_user)
    user = db.recuperer_utilisateur(id_user)
    
    # Enregistrer la visite pour marquer les messages comme lus
    db.update_last_visit(session['user_id'], id_user)
    
    return render_template('discussion.html', messages=messages, user=user, id_user=id_user, session=session)

@app.route('/mon_compte')
def mon_compte():
    user = db.get_user_profile(session['user_id'])
    return render_template('mon_compte.html', user=user)

@app.route('/update_pseudo', methods=['POST'])
def update_pseudo():
    if 'user_id' not in session:
        return redirect('/')
    
    new_pseudo = request.form.get('pseudo')
    if new_pseudo and new_pseudo.strip():
        if db.update_pseudo(session['user_id'], new_pseudo):
            session['user_pseudo'] = new_pseudo
            return redirect('/mon_compte')
        else:
            user = db.get_user_profile(session['user_id'])
            return render_template('mon_compte.html', user=user, erreur_pseudo='Ce pseudo est déjà utilisé')
    return redirect('/mon_compte')

@app.route('/update_password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        return redirect('/')
    
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([old_password, new_password, confirm_password]):
        user = db.get_user_profile(session['user_id'])
        return render_template('mon_compte.html', user=user, erreur_password='Tous les champs sont requis')
    
    if new_password != confirm_password:
        user = db.get_user_profile(session['user_id'])
        return render_template('mon_compte.html', user=user, erreur_password='Les mots de passe ne correspondent pas')
    
    # Vérifier que l'ancien mot de passe est correct
    email = db.get_user_profile(session['user_id'])['email']
    current_user = db.connecter(email, old_password)
    
    if not current_user:
        user = db.get_user_profile(session['user_id'])
        return render_template('mon_compte.html', user=user, erreur_password='Ancien mot de passe incorrect')
    
    db.update_password(session['user_id'], new_password)
    return redirect('/mon_compte')

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect('/')
    
    password = request.form.get('password')
    email = db.get_user_profile(session['user_id'])['email']
    
    # Vérifier le mot de passe
    current_user = db.connecter(email, password)
    if not current_user:
        user = db.get_user_profile(session['user_id'])
        return render_template('mon_compte.html', user=user, erreur_delete='Mot de passe incorrect')
    
    # Supprimer le compte
    db.delete_account(session['user_id'])
    session.clear()
    return redirect('/')

@app.route('/supprimer_message/<int:id_message>', methods=['POST'])
def supprimer_message(id_message):
    if 'user_id' not in session:
        return redirect('/')
    id_user = request.form.get('id_user')
    if id_user:
        db.supprimer_message(id_message, session['user_id'])
        return redirect(f'/discussion/{id_user}')
    return redirect('/accueil')

@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_id' not in session:
        return redirect('/')
    file = request.files.get('avatar')
    if file and file.filename != '':
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        db.update_avatar(session['user_id'], file.filename)
    return redirect('/mon_compte')

# ────────────────────────────────────────────────────────────────────────── 
# ROUTES ADMIN
# ──────────────────────────────────────────────────────────────────────────

def check_admin():
    """Vérifier que l'utilisateur est admin"""
    if 'user_id' not in session or not session.get('user_is_admin'):
        return False
    return True

@app.route('/admin')
def admin_dashboard():
    if not check_admin():
        return redirect('/accueil')
    
    users = db.get_all_users_admin()
    messages = db.get_all_messages_admin()
    return render_template('admin.html', users=users, messages=messages)

@app.route('/admin/user/create', methods=['POST'])
def admin_create_user():
    if not check_admin():
        return redirect('/accueil')
    
    email = request.form.get('email')
    password = request.form.get('password')
    pseudo = request.form.get('pseudo')
    is_admin = int(request.form.get('is_admin', 0))
    
    if email and password and pseudo:
        db.create_user_admin(email, password, pseudo, is_admin)
    
    return redirect('/admin')

@app.route('/admin/user/<int:user_id>/update', methods=['POST'])
def admin_update_user(user_id):
    if not check_admin():
        return redirect('/accueil')
    
    email = request.form.get('email')
    pseudo = request.form.get('pseudo')
    is_admin = int(request.form.get('is_admin', 0))
    
    if email and pseudo:
        db.update_user_admin(user_id, email, pseudo, is_admin)
    
    return redirect('/admin')

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
def admin_delete_user(user_id):
    if not check_admin():
        return redirect('/accueil')
    
    # Empêcher la suppression de son propre compte
    if user_id == session['user_id']:
        return redirect('/admin')
    
    db.delete_user_admin(user_id)
    return redirect('/admin')

@app.route('/admin/message/<int:message_id>/delete', methods=['POST'])
def admin_delete_message(message_id):
    if not check_admin():
        return redirect('/accueil')
    
    db.delete_message_admin(message_id)
    return redirect('/admin')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')