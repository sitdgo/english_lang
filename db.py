# db.py
import psycopg2
from contextlib import closing
from config import DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT


def get_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def create_tables():
    """Создает таблицы и заполняет базу стартовым набором слов."""
    # Оборачиваем подключение в closing для автоматического закрытия
    with closing(get_connection()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id BIGINT PRIMARY KEY
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS words (
                    id SERIAL PRIMARY KEY,
                    target_word VARCHAR(100) NOT NULL UNIQUE,
                    translate_word VARCHAR(100) NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_words (
                    user_id BIGINT REFERENCES users(chat_id) ON DELETE CASCADE,
                    word_id INTEGER REFERENCES words(id) ON DELETE CASCADE,
                    PRIMARY KEY (user_id, word_id)
                );
            """)
            conn.commit()

            cur.execute("SELECT COUNT(*) FROM words;")
            if cur.fetchone()[0] == 0:
                base_words = [
                    ('red', 'красный'), ('blue', 'синий'), ('green', 'зеленый'),
                    ('cat', 'кот'), ('dog', 'собака'), ('house', 'дом'),
                    ('I', 'я'), ('you', 'ты'), ('he', 'он'), ('she', 'она')
                ]
                cur.executemany(
                    "INSERT INTO words (target_word, translate_word) VALUES (%s, %s);",
                    base_words
                )
                conn.commit()


def add_user(chat_id):
    """Добавляет пользователя и привязывает к нему 10 базовых слов."""
    with closing(get_connection()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT chat_id FROM users WHERE chat_id = %s;", (chat_id,))
            if cur.fetchone() is None:
                cur.execute("INSERT INTO users (chat_id) VALUES (%s);", (chat_id,))
                cur.execute("""
                    INSERT INTO user_words (user_id, word_id)
                    SELECT %s, id FROM words LIMIT 10;
                """, (chat_id,))
                conn.commit()


def get_user_words(chat_id):
    """Возвращает список слов пользователя [(id, eng, rus), ...]."""
    with closing(get_connection()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT w.id, w.target_word, w.translate_word 
                FROM words w
                JOIN user_words uw ON w.id = uw.word_id
                WHERE uw.user_id = %s;
            """, (chat_id,))
            return cur.fetchall()


def add_word_to_user(chat_id, eng_word, rus_word):
    """Добавляет новое слово в базу (если нет) и привязывает к пользователю."""
    with closing(get_connection()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO words (target_word, translate_word) 
                VALUES (%s, %s) ON CONFLICT (target_word) DO NOTHING RETURNING id;
            """, (eng_word.lower(), rus_word.lower()))

            result = cur.fetchone()
            if result:
                word_id = result[0]
            else:
                cur.execute("SELECT id FROM words WHERE target_word = %s;", (eng_word.lower(),))
                word_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO user_words (user_id, word_id) 
                VALUES (%s, %s) ON CONFLICT DO NOTHING;
            """, (chat_id, word_id))
            conn.commit()


def delete_user_word(chat_id, eng_word):
    """Удаляет связь слова с конкретным пользователем."""
    with closing(get_connection()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM user_words 
                WHERE user_id = %s AND word_id = (
                    SELECT id FROM words WHERE target_word = %s
                );
            """, (chat_id, eng_word.lower()))
            conn.commit()
