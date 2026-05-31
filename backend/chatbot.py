import re
from database import find_tickets_by_email, find_tickets_by_phone, find_ticket_by_number, update_ticket_status

class ChatBot:
    def __init__(self):
        self.states = {}

    def detect_intent(self, message: str):
        msg = message.strip().lower()
        if any(w in msg for w in ['оператор', 'человек', 'помогите', 'связаться с оператором']):
            return 'operator'
        if any(w in msg for w in ['мой билет', 'покажи билет', 'найти билет', 'где мой билет', 'мои билеты']):
            return 'find_ticket'
        if any(w in msg for w in ['расписание', 'когда', 'поезд', 'маршрут']):
            return 'schedule'
        if any(w in msg for w in ['цена', 'стоимость', 'сколько стоит']):
            return 'price'
        if any(w in msg for w in ['вернуть', 'возврат', 'сдать']):
            return 'refund'
        if any(w in msg for w in ['багаж', 'чемодан', 'ручная кладь']):
            return 'baggage'
        if any(w in msg for w in ['привет', 'здравствуй', 'добрый']):
            return 'greeting'
        return None

    def process_message(self, message: str, session_id: str):
        msg = message.strip().lower()
        state = self.states.get(session_id, {})
        current_intent = state.get('intent')

        # Если есть активный диалог, проверяем, не хочет ли пользователь сменить тему
        if current_intent:
            new_intent = self.detect_intent(message)
            # Если новое сообщение явно относится к другому интенту и это не продолжение (не номер билета и не да/нет)
            if new_intent and new_intent != current_intent:
                # Сбрасываем состояние и обрабатываем как новое сообщение
                del self.states[session_id]
                return self.process_message(message, session_id)

        # Активные диалоги
        if current_intent == 'find_ticket':
            return self._handle_find_ticket_dialog(msg, session_id)
        if current_intent == 'refund':
            return self._handle_refund_dialog(msg, session_id)
        if current_intent == 'schedule':
            return self._handle_schedule_dialog(msg, session_id)

        # Обработка новых запросов (приоритет: оператор > всё остальное)
        # 1. Оператор
        if any(w in msg for w in ['оператор', 'человек', 'помогите', 'связаться с оператором']):
            return {'intent': 'operator', 'confidence': 0.9, 'response': 'Передаю запрос оператору. Ожидайте 1–2 минуты.'}
        # 2. Поиск билета
        if any(w in msg for w in ['мой билет', 'покажи билет', 'найти билет', 'где мой билет', 'мои билеты']):
            self.states[session_id] = {'intent': 'find_ticket', 'step': 0}
            return self._handle_find_ticket_dialog('', session_id)
        # 3. Расписание
        if any(w in msg for w in ['расписание', 'когда', 'поезд', 'маршрут']):
            if 'шереметьево' in msg:
                return {'intent': 'schedule', 'confidence': 0.9, 'response': 'До Шереметьево: каждые 30 мин, в пути 35 мин.'}
            if 'домодедово' in msg:
                return {'intent': 'schedule', 'confidence': 0.9, 'response': 'До Домодедово: каждые 30 мин, в пути 45 мин.'}
            self.states[session_id] = {'intent': 'schedule', 'step': 0}
            return {'intent': 'schedule', 'confidence': 0.7, 'response': 'Куда вам нужно? Напишите "Шереметьево" или "Домодедово".'}
        # 4. Стоимость
        if any(w in msg for w in ['цена', 'стоимость', 'сколько стоит']):
            return {'intent': 'price', 'confidence': 0.9, 'response': 'Стандартный билет — 500 руб., бизнес-класс — 1200 руб., детский (до 7 лет) — бесплатно.'}
        # 5. Возврат
        if any(w in msg for w in ['вернуть', 'возврат', 'сдать']):
            self.states[session_id] = {'intent': 'refund', 'step': 0}
            return {'intent': 'refund', 'confidence': 0.9, 'response': 'Для возврата укажите 10-значный номер билета.'}
        # 6. Багаж
        if any(w in msg for w in ['багаж', 'чемодан', 'ручная кладь']):
            return {'intent': 'baggage', 'confidence': 0.9, 'response': 'Ручная кладь до 36 кг (3 места). Животные в переноске до 8 кг.'}
        # 7. Приветствие
        if any(w in msg for w in ['привет', 'здравствуй', 'добрый', 'здравствуйте']):
            return {'intent': 'greeting', 'confidence': 0.9, 'response': 'Здравствуйте! Я помощник Аэроэкспресс. Спросите о расписании, ценах, багаже или напишите "мой билет".'}
        # 8. Неизвестно
        return {'intent': 'unknown', 'confidence': 0.3, 'response': 'Извините, не понял. Попробуйте спросить иначе или скажите "оператор".'}

    def _handle_find_ticket_dialog(self, msg: str, session_id: str):
        state = self.states.get(session_id, {})
        step = state.get('step', 0)
        if step == 0:
            self.states[session_id]['step'] = 1
            return {'intent': 'find_ticket', 'confidence': 0.9, 'response': 'Для поиска ваших билетов укажите email или номер телефона.'}
        if step == 1:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
            if email_match:
                email = email_match.group()
                tickets = find_tickets_by_email(email)
                self.states[session_id]['tickets'] = tickets
                self.states[session_id]['step'] = 2
                return self._show_tickets_and_ask_action(tickets)
            phone_match = re.search(r'(\+7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}', msg)
            if phone_match:
                phone_raw = phone_match.group()
                digits = re.sub(r'\D', '', phone_raw)
                phone = '+7' + digits if len(digits) == 10 else '+' + digits if len(digits) == 11 else digits
                tickets = find_tickets_by_phone(phone)
                self.states[session_id]['tickets'] = tickets
                self.states[session_id]['step'] = 2
                return self._show_tickets_and_ask_action(tickets)
            return {'intent': 'find_ticket', 'confidence': 0.5, 'response': 'Не удалось распознать email или телефон. Попробуйте ещё раз.'}
        if step == 2:
            if msg in ['нет', 'не надо', 'спасибо', 'отмена']:
                del self.states[session_id]
                return {'intent': 'find_ticket', 'confidence': 0.9, 'response': 'Хорошо. Если понадобится помощь, обращайтесь.'}
            ticket_match = re.search(r'\b\d{10}\b', msg)
            if ticket_match:
                ticket_number = ticket_match.group()
                tickets = self.states[session_id].get('tickets', [])
                if any(t[1] == ticket_number for t in tickets):
                    self.states[session_id] = {'intent': 'refund', 'step': 1, 'ticket_number': ticket_number}
                    return {'intent': 'refund', 'confidence': 0.9, 'response': f'Вы хотите вернуть билет №{ticket_number}. Подтверждаете? (Да/Нет)'}
                else:
                    return {'intent': 'find_ticket', 'confidence': 0.8, 'response': f'Билет {ticket_number} не найден среди ваших. Попробуйте другой номер или напишите "нет".'}
            else:
                return {'intent': 'find_ticket', 'confidence': 0.6, 'response': 'Пожалуйста, укажите номер билета (10 цифр) для возврата, или напишите "нет".'}
        del self.states[session_id]
        return {'intent': 'find_ticket', 'confidence': 0.5, 'response': 'Ошибка. Напишите "мой билет", чтобы начать заново.'}

    def _handle_refund_dialog(self, msg: str, session_id: str):
        state = self.states.get(session_id, {})
        step = state.get('step', 0)
        if step == 0:
            ticket_match = re.search(r'\b\d{10}\b', msg)
            if ticket_match:
                ticket_number = ticket_match.group()
                ticket = find_ticket_by_number(ticket_number)
                if ticket:
                    if ticket[8] == 'active':
                        self.states[session_id]['ticket_number'] = ticket_number
                        self.states[session_id]['step'] = 1
                        return {'intent': 'refund', 'confidence': 0.9, 'response': f'Найден билет {ticket_number}. Подтверждаете возврат? (Да/Нет)'}
                    else:
                        del self.states[session_id]
                        return {'intent': 'refund', 'confidence': 0.8, 'response': f'Билет {ticket_number} уже {ticket[8]}. Возврат невозможен.'}
                else:
                    return {'intent': 'refund', 'confidence': 0.7, 'response': f'Билет {ticket_number} не найден. Проверьте номер.'}
            else:
                return {'intent': 'refund', 'confidence': 0.5, 'response': 'Пожалуйста, введите 10-значный номер билета.'}
        if step == 1:
            if msg in ['да', 'конечно', 'давай', 'подтверждаю']:
                update_ticket_status(state.get('ticket_number'), 'refunded')
                del self.states[session_id]
                return {'intent': 'refund', 'confidence': 0.95, 'response': f'✅ Возврат билета {state["ticket_number"]} оформлен. Деньги поступят в течение 5–10 дней.'}
            elif msg in ['нет', 'отмена', 'не надо']:
                del self.states[session_id]
                return {'intent': 'refund', 'confidence': 0.9, 'response': 'Возврат отменён. Если передумаете, напишите снова.'}
            else:
                return {'intent': 'refund', 'confidence': 0.6, 'response': 'Пожалуйста, ответьте "Да" или "Нет".'}
        del self.states[session_id]
        return {'intent': 'refund', 'confidence': 0.5, 'response': 'Ошибка. Начните заново.'}

    def _handle_schedule_dialog(self, msg: str, session_id: str):
        if 'шереметьево' in msg:
            del self.states[session_id]
            return {'intent': 'schedule', 'confidence': 0.9, 'response': 'До Шереметьево: каждые 30 мин, в пути 35 мин.'}
        if 'домодедово' in msg:
            del self.states[session_id]
            return {'intent': 'schedule', 'confidence': 0.9, 'response': 'До Домодедово: каждые 30 мин, в пути 45 мин.'}
        return {'intent': 'schedule', 'confidence': 0.7, 'response': 'Уточните маршрут: "Шереметьево" или "Домодедово".'}

    def _show_tickets_and_ask_action(self, tickets):
        if not tickets:
            return {'intent': 'find_ticket', 'confidence': 0.9, 'response': 'Билеты не найдены. Проверьте правильность ввода.'}
        response = "🎫 Найдены ваши билеты:\n\n"
        for t in tickets:
            response += f"• Номер: {t[1]}\n  Маршрут: {t[5]}\n  Дата: {t[6]}, отправление: {t[7]}\n  Статус: {t[8]}\n\n"
        response += "Если хотите вернуть один из билетов, напишите его номер (10 цифр). Если нет – ответьте «нет»."
        return {'intent': 'find_ticket', 'confidence': 0.9, 'response': response}

chatbot = ChatBot()