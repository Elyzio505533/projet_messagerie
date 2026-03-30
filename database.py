import sqlite3
from datetime import datetime, timedelta

class DatabaseManager:
    def __init__(self, db_name='blinky.db'):
        self.dbname = db_name
        self.creer_tables()
        self.creer_admin_default()
    
    def get_connexion(self):
        conn = sqlite3.connect(self.dbname, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def creer_tables(self):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS USERS (
                    id_user INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    pseudo TEXT UNIQUE NOT NULL,
                    is_admin BOOLEAN NOT NULL,
                    avatar TEXT DEFAULT 'default.png'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS MESSAGES (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    datetime DATETIME NOT NULL,
                    id_sender INTEGER,
                    id_receiver INTEGER,
                    FOREIGN KEY (id_sender) REFERENCES users(id_user),
                    FOREIGN KEY (id_receiver) REFERENCES users(id_user)
                )
            ''')

            conn.commit()
        finally:
            conn.close()

    def inscrire(self, email, mot_de_passe, pseudo, is_admin=0):
        import hashlib
        mdp_hash = hashlib.sha256(mot_de_passe.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            conn.execute(
                'INSERT INTO users (email, password, pseudo, is_admin) VALUES (?,?,?,?)',
                (email, mdp_hash, pseudo, is_admin)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def connecter(self, email, mot_de_passe):
        import hashlib
        mdp_hash = hashlib.sha256(mot_de_passe.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            user = conn.execute(
                'SELECT * FROM users WHERE email=? AND password=?',
                (email, mdp_hash)
            ).fetchone()
        finally:
            conn.close()
        return user

    def creer_admin_default(self):
        self.inscrire('admin@blinky.com', 'admin123', 'Admin', 1)

    def supprimer_utilisateur(self, user_id):
        conn = self.get_connexion()
        try:
            conn.execute('DELETE FROM users WHERE id=?', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def creer_message(self, content, id_sender, id_receiver):
        conn = self.get_connexion()
        try:
            now = datetime.now()
            rounded_datetime = now.replace(second=0, microsecond=0)
            conn.execute(
                'INSERT INTO messages (content, datetime, id_sender, id_receiver) VALUES (?,?,?,?)',
                (content, rounded_datetime.strftime("%Y-%m-%d %H:%M"), id_sender, id_receiver)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def recuperer_utilisateurs(self):
        conn = self.get_connexion()
        try:
            users = conn.execute('SELECT id_user, pseudo, is_admin FROM users').fetchall()
            return users
        finally:
            conn.close()

    def recuperer_messages(self, id_user1, id_user2):
        conn = self.get_connexion()
        try:
            messages = conn.execute(
                '''
                SELECT id, content, datetime, id_sender, id_receiver
                FROM messages
                WHERE (id_sender=? AND id_receiver=?) OR (id_sender=? AND id_receiver=?)
                ORDER BY datetime ASC
                ''',
                (id_user1, id_user2, id_user2, id_user1)
            ).fetchall()
            return messages
        finally:
            conn.close()
    
    def recuperer_discussions(self, id_user):
        conn = self.get_connexion()
        try:
            discussions = conn.execute('''
                SELECT DISTINCT id_user, pseudo, is_admin, avatar FROM USERS
                WHERE id_user IN (
                    SELECT id_sender FROM MESSAGES WHERE id_receiver = ?
                    UNION
                    SELECT id_receiver FROM MESSAGES WHERE id_sender = ?
                )
            ''', (id_user, id_user)).fetchall()
            
            return discussions
        finally:
            conn.close()
    
    def recuperer_utilisateur(self, user_id):
        conn = self.get_connexion()
        try:
            user = conn.execute('SELECT id_user, pseudo, is_admin FROM users WHERE id_user=?', (user_id,)).fetchone()
            return user
        finally: conn.close()

    def recuperer_utilisateurs(self):
        conn = self.get_connexion()
        try:
            users = conn.execute('SELECT id_user, pseudo, is_admin, avatar FROM users').fetchall()
            return users
        finally:
            conn.close()
    
    def supprimer_message(self, id_message, id_user):
        conn = self.get_connexion()
        try:
            message = conn.execute(
                'SELECT id_sender FROM messages WHERE id=?',
                (id_message,)
            ).fetchone()
            if message and message['id_sender'] == id_user:
                conn.execute('DELETE FROM messages WHERE id=?', (id_message,))
                conn.commit()
                return True
            return False
        finally:
            conn.close()

    def update_avatar(self, user_id, filename):
        conn = self.get_connexion()
        try:
            conn.execute(
                'UPDATE users SET avatar=? WHERE id_user=?',
                (filename, user_id)
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_user_profile(self, user_id):
        conn = self.get_connexion()
        try:
            user = conn.execute(
                'SELECT id_user, email, pseudo, avatar FROM users WHERE id_user=?',
                (user_id,)
            ).fetchone()
            return user
        finally:
            conn.close()
    
    def update_pseudo(self, user_id, new_pseudo):
        conn = self.get_connexion()
        try:
            # Vérifier que le pseudo n'existe pas déjà
            existing = conn.execute(
                'SELECT id_user FROM users WHERE pseudo=? AND id_user!=?',
                (new_pseudo, user_id)
            ).fetchone()
            
            if existing:
                return False
            
            conn.execute(
                'UPDATE users SET pseudo=? WHERE id_user=?',
                (new_pseudo, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def update_password(self, user_id, new_password):
        import hashlib
        mdp_hash = hashlib.sha256(new_password.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            conn.execute(
                'UPDATE users SET password=? WHERE id_user=?',
                (mdp_hash, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def delete_account(self, user_id):
        conn = self.get_connexion()
        try:
            # Supprimer tous les messages de l'utilisateur
            conn.execute('DELETE FROM messages WHERE id_sender=? OR id_receiver=?', (user_id, user_id))
            # Supprimer l'utilisateur
            conn.execute('DELETE FROM users WHERE id_user=?', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    
    # ────────────────────────────────────────────────────────────────────────── 
    # FONCTIONS ADMIN
    # ──────────────────────────────────────────────────────────────────────────
    
    def get_all_users_admin(self):
        conn = self.get_connexion()
        try:
            users = conn.execute(
                'SELECT id_user, email, pseudo, is_admin FROM users ORDER BY id_user DESC'
            ).fetchall()
            return users
        finally:
            conn.close()
    
    def get_all_messages_admin(self):
        conn = self.get_connexion()
        try:
            messages = conn.execute('''
                SELECT m.id, m.content, m.datetime, m.id_sender, m.id_receiver,
                       u1.pseudo as sender_pseudo, u2.pseudo as receiver_pseudo
                FROM messages m
                LEFT JOIN users u1 ON m.id_sender = u1.id_user
                LEFT JOIN users u2 ON m.id_receiver = u2.id_user
                ORDER BY m.datetime DESC
            ''').fetchall()
            return messages
        finally:
            conn.close()
    
    def create_user_admin(self, email, password, pseudo, is_admin=0):
        return self.inscrire(email, password, pseudo, is_admin)
    
    def update_user_admin(self, user_id, email, pseudo, is_admin):
        conn = self.get_connexion()
        try:
            # Vérifier que l'email/pseudo n'existent pas déjà
            existing_email = conn.execute(
                'SELECT id_user FROM users WHERE email=? AND id_user!=?',
                (email, user_id)
            ).fetchone()
            
            existing_pseudo = conn.execute(
                'SELECT id_user FROM users WHERE pseudo=? AND id_user!=?',
                (pseudo, user_id)
            ).fetchone()
            
            if existing_email or existing_pseudo:
                return False
            
            conn.execute(
                'UPDATE users SET email=?, pseudo=?, is_admin=? WHERE id_user=?',
                (email, pseudo, is_admin, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def delete_user_admin(self, user_id):
        # Ne pas supprimer l'admin par défaut
        if user_id == 1:
            return False
        
        conn = self.get_connexion()
        try:
            # Supprimer tous les messages de l'utilisateur
            conn.execute('DELETE FROM messages WHERE id_sender=? OR id_receiver=?', (user_id, user_id))
            # Supprimer l'utilisateur
            conn.execute('DELETE FROM users WHERE id_user=?', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def delete_message_admin(self, message_id):
        conn = self.get_connexion()
        try:
            conn.execute('DELETE FROM messages WHERE id=?', (message_id,))
            conn.commit()
            return True
        finally:
            conn.close()
