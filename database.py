import psycopg2
import psycopg2.extras
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        self.database_url = os.environ.get('DATABASE_URL')
        self.creer_tables()
        self.creer_admin_default()

    def get_connexion(self):
        conn = psycopg2.connect(self.database_url)
        return conn

    def _fetchone_as_dict(self, cursor):
        row = cursor.fetchone()
        if row is None:
            return None
        cols = [desc[0] for desc in cursor.description]
        return dict(zip(cols, row))

    def _fetchall_as_dict(self, cursor):
        cols = [desc[0] for desc in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def creer_tables(self):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id_user SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    pseudo TEXT UNIQUE NOT NULL,
                    is_admin BOOLEAN NOT NULL,
                    avatar TEXT DEFAULT 'default.png'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    datetime TIMESTAMP NOT NULL,
                    id_sender INTEGER REFERENCES users(id_user),
                    id_receiver INTEGER REFERENCES users(id_user)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discussion_visits (
                    id SERIAL PRIMARY KEY,
                    id_user INTEGER NOT NULL REFERENCES users(id_user),
                    id_other_user INTEGER NOT NULL REFERENCES users(id_user),
                    last_visit TIMESTAMP NOT NULL,
                    UNIQUE(id_user, id_other_user)
                )
            ''')

            conn.commit()
        finally:
            conn.close()

    def inscrire(self, email, mot_de_passe, pseudo, is_admin=False):
        import hashlib
        mdp_hash = hashlib.sha256(mot_de_passe.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (email, password, pseudo, is_admin) VALUES (%s, %s, %s, %s)',
                (email, mdp_hash, pseudo, is_admin)
            )
            conn.commit()
            return True
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            return False
        finally:
            conn.close()

    def connecter(self, email, mot_de_passe):
        import hashlib
        mdp_hash = hashlib.sha256(mot_de_passe.encode('utf-8')).hexdigest()
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM users WHERE email=%s AND password=%s',
                (email, mdp_hash)
            )
            return self._fetchone_as_dict(cursor)
        finally:
            conn.close()

    def creer_admin_default(self):
        self.inscrire('admin@blinky.com', 'admin123', 'Admin', True)
        self.update_avatar(1, 'admin.jpg')

    def supprimer_utilisateur(self, user_id):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id_user=%s', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def creer_message(self, content, id_sender, id_receiver):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO messages (content, datetime, id_sender, id_receiver) VALUES (%s, %s, %s, %s)',
                (content, datetime.now(), id_sender, id_receiver)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def recuperer_messages(self, id_user1, id_user2):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, content, datetime, id_sender, id_receiver
                FROM messages
                WHERE (id_sender=%s AND id_receiver=%s) OR (id_sender=%s AND id_receiver=%s)
                ORDER BY datetime ASC
                ''',
                (id_user1, id_user2, id_user2, id_user1)
            )
            return self._fetchall_as_dict(cursor)
        finally:
            conn.close()

    def recuperer_discussions(self, id_user):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT id_user, pseudo, is_admin, avatar FROM users
                WHERE id_user IN (
                    SELECT id_sender FROM messages WHERE id_receiver = %s
                    UNION
                    SELECT id_receiver FROM messages WHERE id_sender = %s
                )
            ''', (id_user, id_user))
            return self._fetchall_as_dict(cursor)
        finally:
            conn.close()

    def recuperer_utilisateur(self, user_id):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id_user, pseudo, is_admin FROM users WHERE id_user=%s', (user_id,))
            return self._fetchone_as_dict(cursor)
        finally:
            conn.close()

    def recuperer_utilisateurs(self):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id_user, pseudo, is_admin, avatar FROM users')
            return self._fetchall_as_dict(cursor)
        finally:
            conn.close()

    def supprimer_message(self, id_message, id_user):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id_sender FROM messages WHERE id=%s', (id_message,))
            message = self._fetchone_as_dict(cursor)
            if message and message['id_sender'] == id_user:
                cursor.execute('DELETE FROM messages WHERE id=%s', (id_message,))
                conn.commit()
                return True
            return False
        finally:
            conn.close()

    def update_avatar(self, user_id, filename):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET avatar=%s WHERE id_user=%s',
                (filename, user_id)
            )
            conn.commit()
        finally:
            conn.close()

    def get_user_profile(self, user_id):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id_user, email, pseudo, avatar FROM users WHERE id_user=%s',
                (user_id,)
            )
            return self._fetchone_as_dict(cursor)
        finally:
            conn.close()

    def update_pseudo(self, user_id, new_pseudo):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id_user FROM users WHERE pseudo=%s AND id_user!=%s',
                (new_pseudo, user_id)
            )
            if self._fetchone_as_dict(cursor):
                return False
            cursor.execute(
                'UPDATE users SET pseudo=%s WHERE id_user=%s',
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
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET password=%s WHERE id_user=%s',
                (mdp_hash, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_account(self, user_id):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE id_sender=%s OR id_receiver=%s', (user_id, user_id))
            cursor.execute('DELETE FROM users WHERE id_user=%s', (user_id,))
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
            cursor = conn.cursor()
            cursor.execute('SELECT id_user, email, pseudo, is_admin FROM users ORDER BY id_user DESC')
            return self._fetchall_as_dict(cursor)
        finally:
            conn.close()

    def get_all_messages_admin(self):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT m.id, m.content, m.datetime, m.id_sender, m.id_receiver,
                       u1.pseudo as sender_pseudo, u2.pseudo as receiver_pseudo
                FROM messages m
                LEFT JOIN users u1 ON m.id_sender = u1.id_user
                LEFT JOIN users u2 ON m.id_receiver = u2.id_user
                ORDER BY m.datetime DESC
            ''')
            return self._fetchall_as_dict(cursor)
        finally:
            conn.close()

    def create_user_admin(self, email, password, pseudo, is_admin=False):
        return self.inscrire(email, password, pseudo, is_admin)

    def update_user_admin(self, user_id, email, pseudo, is_admin):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id_user FROM users WHERE email=%s AND id_user!=%s',
                (email, user_id)
            )
            if self._fetchone_as_dict(cursor):
                return False
            cursor.execute(
                'SELECT id_user FROM users WHERE pseudo=%s AND id_user!=%s',
                (pseudo, user_id)
            )
            if self._fetchone_as_dict(cursor):
                return False
            cursor.execute(
                'UPDATE users SET email=%s, pseudo=%s, is_admin=%s WHERE id_user=%s',
                (email, pseudo, is_admin, user_id)
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_user_admin(self, user_id):
        if user_id == 1:
            return False
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE id_sender=%s OR id_receiver=%s', (user_id, user_id))
            cursor.execute('DELETE FROM users WHERE id_user=%s', (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_message_admin(self, message_id):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE id=%s', (message_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ──────────────────────────────────────────────────────────────────────────
    # SYSTÈME DE NOTIFICATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def update_last_visit(self, id_user, id_other_user):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute(
                'SELECT id FROM discussion_visits WHERE id_user=%s AND id_other_user=%s',
                (id_user, id_other_user)
            )
            existing = self._fetchone_as_dict(cursor)
            if existing:
                cursor.execute(
                    'UPDATE discussion_visits SET last_visit=%s WHERE id_user=%s AND id_other_user=%s',
                    (now, id_user, id_other_user)
                )
            else:
                cursor.execute(
                    'INSERT INTO discussion_visits (id_user, id_other_user, last_visit) VALUES (%s, %s, %s)',
                    (id_user, id_other_user, now)
                )
            conn.commit()
        finally:
            conn.close()

    def get_last_visit(self, id_user, id_other_user):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT last_visit FROM discussion_visits WHERE id_user=%s AND id_other_user=%s',
                (id_user, id_other_user)
            )
            visit = self._fetchone_as_dict(cursor)
            return visit['last_visit'] if visit else None
        finally:
            conn.close()

    def count_unread_messages(self, id_user, id_other_user):
        conn = self.get_connexion()
        try:
            cursor = conn.cursor()
            last_visit = self.get_last_visit(id_user, id_other_user)
            if last_visit is None:
                cursor.execute(
                    'SELECT COUNT(*) as cnt FROM messages WHERE id_receiver=%s AND id_sender=%s',
                    (id_user, id_other_user)
                )
            else:
                cursor.execute(
                    'SELECT COUNT(*) as cnt FROM messages WHERE id_receiver=%s AND id_sender=%s AND datetime > %s',
                    (id_user, id_other_user, last_visit)
                )
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()