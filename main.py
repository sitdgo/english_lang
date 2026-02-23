# main.py
import random
import telebot
from telebot import types
from config import TOKEN
import db

bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных при запуске скрипта
db.create_tables()

# Глобальный словарь для отслеживания текущего правильного ответа пользователя
user_states = {}


def create_markup(correct_word, other_words):
    """Создает клавиатуру с 4 вариантами ответа и сервисными кнопками."""
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    # Собираем 4 варианта ответов (русские переводы)
    options = [correct_word[2]] + [w[2] for w in other_words]
    random.shuffle(options)

    buttons = [types.KeyboardButton(text=opt) for opt in options]
    markup.add(*buttons)

    # Добавляем нижний ряд сервисных кнопок
    row = [
        types.KeyboardButton("Дальше ⏭"),
        types.KeyboardButton("Добавить слово ➕"),
        types.KeyboardButton("Удалить слово 🔙")
    ]
    markup.add(*row)
    return markup


def send_next_question(chat_id):
    """Формирует и отправляет следующий вопрос."""
    words = db.get_user_words(chat_id)
    if len(words) < 4:
        bot.send_message(chat_id, "У вас должно быть минимум 4 слова для тренировки! Добавьте новые.")
        return

    # Выбираем правильное слово и 3 неправильных
    correct_word = random.choice(words)
    other_words = random.sample([w for w in words if w[0] != correct_word[0]], 3)

    # Запоминаем правильный ответ
    user_states[chat_id] = correct_word[2]

    markup = create_markup(correct_word, other_words)
    bot.send_message(
        chat_id,
        f"Угадай перевод слова:\n🇬🇧 <b>{correct_word[1]}</b>",
        reply_markup=markup,
        parse_mode='HTML'
    )


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    db.add_user(chat_id)

    welcome_text = (
        "Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.\n\n"
        "У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспользуйся инструментами:\n"
        "добавить слово ➕,\n"
        "удалить слово 🔙.\n\n"
        "Ну что, начнём ⬇️"
    )
    bot.send_message(chat_id, welcome_text)
    send_next_question(chat_id)


@bot.message_handler(func=lambda message: message.text == "Дальше ⏭")
def next_word(message):
    send_next_question(message.chat.id)


@bot.message_handler(func=lambda message: message.text == "Добавить слово ➕")
def add_word_step_1(message):
    msg = bot.send_message(message.chat.id, "Введи новое слово на английском языке:")
    bot.register_next_step_handler(msg, add_word_step_2)


def add_word_step_2(message):
    eng_word = message.text
    msg = bot.send_message(message.chat.id, f"Теперь введи перевод для слова '{eng_word}':")
    bot.register_next_step_handler(msg, add_word_step_3, eng_word)


def add_word_step_3(message, eng_word):
    rus_word = message.text
    chat_id = message.chat.id
    db.add_word_to_user(chat_id, eng_word, rus_word)

    total_words = len(db.get_user_words(chat_id))
    bot.send_message(chat_id, f"Слово добавлено! 📚 Теперь ты изучаешь {total_words} слов.")
    send_next_question(chat_id)


@bot.message_handler(func=lambda message: message.text == "Удалить слово 🔙")
def delete_word_step_1(message):
    msg = bot.send_message(message.chat.id, "Введи английское слово, которое хочешь удалить:")
    bot.register_next_step_handler(msg, delete_word_step_2)


def delete_word_step_2(message):
    eng_word = message.text
    chat_id = message.chat.id
    db.delete_user_word(chat_id, eng_word)
    bot.send_message(chat_id, f"Слово '{eng_word}' удалено из твоего словаря.")
    send_next_question(chat_id)


@bot.message_handler(func=lambda message: True)
def check_answer(message):
    chat_id = message.chat.id
    text = message.text

    # Проверяем, есть ли активный вопрос для пользователя
    if chat_id in user_states:
        correct_answer = user_states[chat_id]
        if text == correct_answer:
            bot.send_message(chat_id, "✅ Верно!")
            send_next_question(chat_id)
        else:
            bot.send_message(chat_id, "❌ Неправильно. Попробуй еще раз!")
    else:
        bot.send_message(chat_id, "Используй кнопки меню.")


if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)
