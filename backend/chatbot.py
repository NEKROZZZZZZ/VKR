import re
import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INTENTS = {
    'greeting': ['привет', 'здравствуйте', 'добрый день', 'доброе утро', 'добрый вечер', 'салют'],
    'farewell': ['пока', 'до свидания', 'всего хорошего', 'удачи', 'прощай'],
    'schedule': ['расписание', 'когда', 'во сколько', 'отправление', 'прибытие', 'поезд', 'маршрут'],
    'ticket_price': ['сколько стоит', 'цена', 'стоимость', 'билет', 'купить', 'приобрести'],
    'refund': ['вернуть', 'возврат', 'сдать билет', 'отмена', 'деньги назад'],
    'baggage_rules': ['багаж', 'чемодан', 'ручная кладь', 'вещи', 'провоз', 'животные'],
    'operator': ['оператор', 'человек', 'помогите', 'соедините'],
    'delay_info': ['задержка', 'опоздание', 'отмена', 'перенесли']
}

INTENT_RESPONSES = {
    'greeting': "Здравствуйте! Я виртуальный помощник «Аэроэкспресс». Чем могу помочь?",
    'farewell': "Спасибо за обращение! Хорошего дня и приятной поездки! 👋",
    'schedule': "📍 Расписание: до Шереметьево каждые 30 мин, до Домодедово каждые 30 мин. Уточните маршрут?",
    'ticket_price': "💰 Стандартный билет: 500 руб., Бизнес-класс: 1200 руб., Детский (до 7 лет) — бесплатно.",
    'refund': "🔄 Для возврата нужен номер билета (10 цифр). Напишите его, пожалуйста.",
    'baggage_rules': "🧳 Ручная кладь: до 36 кг (3 места). Животные: в переноске до 8 кг. Подробнее на сайте.",
    'operator': "🔄 Соединяю с оператором... Ожидайте 1-2 минуты.",
    'delay_info': "⏰ Информация о задержках на сайте и в приложении. Приносим извинения.",
    'unknown': "Извините, я не понял. Попробуйте переформулировать или скажите «оператор»."
}

class ChatBot:
    def __init__(self):
        self.session_states = {}  # для многошаговых диалогов

    def process_message(self, message: str, session_key: str) -> Dict:
        message = message.strip().lower()
        if not message:
            return {'intent': 'empty', 'confidence': 0.0, 'response': "Напишите ваш вопрос."}

        intent, confidence = self._classify(message)
        should_escalate = (intent == 'operator')

        # Если мы в режиме сбора номера билета
        state = self.session_states.get(session_key, {})
        if state.get('awaiting_ticket'):
            if re.search(r'\b\d{10}\b', message):
                ticket = re.search(r'\b\d{10}\b', message).group()
                response = f"✅ Билет №{ticket} найден. Заявка на возврат оформлена. Деньги вернутся в течение 5-10 дней."
                del self.session_states[session_key]
            else:
                response = "Не удалось распознать номер. Пожалуйста, введите 10 цифр с билета."
            return {'intent': 'refund', 'confidence': 0.9, 'response': response, 'should_escalate': False}

        # Запуск сбора номера для возврата
        if intent == 'refund' and 'номер' not in message:
            self.session_states[session_key] = {'awaiting_ticket': True}
            response = "Укажите номер билета (10 цифр) для оформления возврата."
        else:
            response = INTENT_RESPONSES.get(intent, INTENT_RESPONSES['unknown'])

        if intent == 'farewell' and session_key in self.session_states:
            del self.session_states[session_key]

        return {
            'intent': intent,
            'confidence': confidence,
            'response': response,
            'should_escalate': should_escalate
        }

    def _classify(self, text: str) -> Tuple[str, float]:
        best_intent = 'unknown'
        best_score = 0.0
        for intent, keywords in INTENTS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_intent = intent
        confidence = min(0.5 + best_score * 0.1, 0.95) if best_score else 0.3
        return best_intent, confidence

    def reset_session(self, session_key: str):
        if session_key in self.session_states:
            del self.session_states[session_key]

chatbot = ChatBot()