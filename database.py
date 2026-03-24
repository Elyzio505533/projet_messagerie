import sqlite3
from datetime import datetime

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
                    is_admin BOOLEAN NOT NULL DEFAULT 0
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

    def inscrire(self, email, mot_de_passe, pseudo):
        import hashlib
        mdp_hash = hashlib.sha256(mot_de_passe.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            conn.execute(
                'INSERT INTO users (email, password, pseudo) VALUES (?,?,?)',
                (email, mdp_hash, pseudo)
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
        self.inscrire('admin@blinky.com', 'admin123', 'Admin')

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
            conn.execute(
                'INSERT INTO messages (content, datetime, id_sender, id_receiver) VALUES (?,?,?,?)',
                (content, datetime.now(), id_sender, id_receiver)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def recuperer_utilisateurs(self):
        conn = self.get_connexion()
        try:
            users = conn.execute('SELECT id_user, pseudo FROM users').fetchall()
            return users
        finally:
            conn.close()

    def recuperer_messages(self, id_user1, id_user2):
        conn = self.get_connexion()
        try:
            messages = conn.execute(
                '''
                SELECT content, datetime, id_sender, id_receiver
                FROM messages
                WHERE (id_sender=? AND id_receiver=?) OR (id_sender=? AND id_receiver=?)
                ORDER BY datetime ASC
                ''',
                (id_user1, id_user2, id_user2, id_user1)
            ).fetchall()
            return messages
        finally:
            conn.close()