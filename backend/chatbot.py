import re
from database import find_tickets_by_email, find_tickets_by_phone, find_ticket_by_number, update_ticket_status

class ChatBot:
    def __init__(self):
        self.states = {}

    def _detect_intent(self, msg: str):
        """Возвращает имя интента по сообщению (без сохранения состояния)"""
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
        if any(w in msg for w in ['оператор', 'человек', 'помогите']):
            return 'operator'
        if any(w in msg for w in ['привет', 'здравствуй', 'добрый', 'здравствуйте']):
            return 'greeting'
        return None

    def process_message(self, message: str, session_id: str) -> dict:
        msg = message.strip().lower()
        state = self.states.get(session_id, {})
        current_intent = state.get('intent')
        step = state.get('step', 0)

        # Если есть активный диалог и новое сообщение не является ожидаемым продолжением
        if current_intent and step >= 0:
            # Определяем, является ли сообщение ожидаемым для текущего шага
            expected = False
            if current_intent == 'find_ticket':
                if step == 0:
                    expected = False  # только переход на шаг 1
                elif step == 1:
                    # ожидаем email или телефон
                    if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg) or re.search(r'(\+7|8)?[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{2}[\s\-]?[0-9]{2}', msg):
                        expected = True
                elif step == 2:
                    # ожидаем номер билета (10 цифр) или "нет"
                    if re.search(r'\b\d{10}\b', msg) or msg in ['нет', 'не надо', 'спасибо', 'отмена']:
                        expected = True
            elif current_intent == 'refund':
                if step == 0:
                    # ожидаем номер билета (10 цифр)
                    if re.search(r'\b\d{10}\b', msg):
                        expected = True
                elif step == 1:
                    # ожидаем да/нет
                    if msg in ['да', 'конечно', 'давай', 'подтверждаю', 'нет', 'отмена', 'не надо']:
                        expected = True
            elif current_intent == 'schedule' and step == 0:
                # ожидаем название маршрута
                if 'шереметьево' in msg or 'домодедово' in msg:
                    expected = True
            elif current_intent == 'unknown' and step == 0:
                expected = True  # диалог уточнения

            # Если сообщение не ожидается — сбрасываем состояние и обрабатываем как новое
            if not expected:
                del self.states[session_id]
                return self.process_message(message, session_id)

        # Активные диалоги
        if current_intent == 'find_ticket':
            return self._handle_find_ticket_dialog(msg, session_id)
        if current_intent == 'refund':
            return self._handle_refund_dialog(msg, session_id)
        if current_intent == 'schedule':
            return self._handle_schedule_dialog(msg, session_id)
        if current_intent == 'unknown':
            return self._handle_unknown_dialog(msg, session_id)

        # ---- Поиск билета ----
        if any(w in msg for w in ['мой билет', 'покажи билет', 'найти билет', 'где мой билет', 'мои билеты']):
            self.states[session_id] = {'intent': 'find_ticket', 'step': 0}
            return self._handle_find_ticket_dialog('', session_id)

        # ---- Расписание ----
        if any(w in msg for w in ['расписание', 'когда', 'поезд', 'маршрут']):
            if 'шереметьево' in msg:
                return {'intent': 'schedule', 'confidence': 0.9,
                        'response': 'До Шереметьево: каждые 30 мин, в пути 35 мин.'}
            if 'домодедово' in msg:
                return {'intent': 'schedule', 'confidence': 0.9,
                        'response': 'До Домодедово: каждые 30 мин, в пути 45 мин.'}
            self.states[session_id] = {'intent': 'schedule', 'step': 0}
            return {'intent': 'schedule', 'confidence': 0.7,
                    'response': 'Куда вам нужно? Напишите "Шереметьево" или "Домодедово".'}

        # ---- Стоимость ----
        if any(w in msg for w in ['цена', 'стоимость', 'сколько стоит']):
            return {'intent': 'price', 'confidence': 0.9,
                    'response': 'Стандартный билет — 500 руб., бизнес-класс — 1200 руб., детский (до 7 лет) — бесплатно.'}

        # ---- Возврат билета ----
        if any(w in msg for w in ['вернуть', 'возврат', 'сдать']):
            self.states[session_id] = {'intent': 'refund', 'step': 0}
            return {'intent': 'refund', 'confidence': 0.9,
                    'response': 'Для возврата укажите 10-значный номер билета.'}

        # ---- Багаж ----
        if any(w in msg for w in ['багаж', 'чемодан', 'ручная кладь']):
            return {'intent': 'baggage', 'confidence': 0.9,
                    'response': 'Ручная кладь до 36 кг (3 места). Животные в переноске до 8 кг.'}

        # ---- Оператор ----
        if any(w in msg for w in ['оператор', 'человек', 'помогите']):
            return {'intent': 'operator', 'confidence': 0.9,
                    'response': 'Передаю запрос оператору. Ожидайте 1–2 минуты.'}

        # ---- Приветствие ----
        if any(w in msg for w in ['привет', 'здравствуй', 'добрый', 'здравствуйте']):
            return {'intent': 'greeting', 'confidence': 0.9,
                    'response': 'Здравствуйте! Я помощник Аэроэкспресс. Спросите о расписании, ценах, багаже или напишите "мой билет".'}

        # ---- Неизвестно ----
        self.states[session_id] = {'intent': 'unknown', 'step': 0}
        return self._handle_unknown_dialog(msg, session_id)

    # ----- Диалог поиска билетов -----
    def _handle_find_ticket_dialog(self, msg: str, session_id: str):
        state = self.states.get(session_id, {})
        step = state.get('step', 0)

        if step == 0:
            self.states[session_id]['step'] = 1
            return {'intent': 'find_ticket', 'confidence': 0.9,
                    'response': 'Для поиска ваших билетов укажите email или номер телефона.'}

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
                if len(digits) == 10:
                    phone = '+7' + digits
                elif len(digits) == 11:
                    phone = '+' + digits
                else:
                    phone = digits
                tickets = find_tickets_by_phone(phone)
                self.states[session_id]['tickets'] = tickets
                self.states[session_id]['step'] = 2
                return self._show_tickets_and_ask_action(tickets)

            return {'intent': 'find_ticket', 'confidence': 0.5,
                    'response': 'Не удалось распознать email или телефон. Попробуйте ещё раз.'}

        if step == 2:
            if msg in ['нет', 'не надо', 'спасибо', 'отмена']:
                del self.states[session_id]
                return {'intent': 'find_ticket', 'confidence': 0.9,
                        'response': 'Хорошо. Если понадобится помощь, обращайтесь.'}
            ticket_match = re.search(r'\b\d{10}\b', msg)
            if ticket_match:
                ticket_number = ticket_match.group()
                tickets = self.states[session_id].get('tickets', [])
                ticket_exists = any(t[1] == ticket_number for t in tickets)
                if ticket_exists:
                    self.states[session_id] = {'intent': 'refund', 'step': 1, 'ticket_number': ticket_number}
                    return {'intent': 'refund', 'confidence': 0.9,
                            'response': f'Вы хотите вернуть билет №{ticket_number}. Подтверждаете? (Да/Нет)'}
                else:
                    return {'intent': 'find_ticket', 'confidence': 0.8,
                            'response': f'Билет {ticket_number} не найден среди ваших. Попробуйте другой номер или напишите "нет".'}
            else:
                return {'intent': 'find_ticket', 'confidence': 0.6,
                        'response': 'Пожалуйста, укажите номер билета (10 цифр) для возврата, или напишите "нет".'}

        del self.states[session_id]
        return {'intent': 'find_ticket', 'confidence': 0.5,
                'response': 'Ошибка. Напишите "мой билет", чтобы начать заново.'}

    # ----- Диалог возврата -----
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
                        return {'intent': 'refund', 'confidence': 0.9,
                                'response': f'Найден билет {ticket_number}. Подтверждаете возврат? (Да/Нет)'}
                    else:
                        del self.states[session_id]
                        return {'intent': 'refund', 'confidence': 0.8,
                                'response': f'Билет {ticket_number} уже {ticket[8]}. Возврат невозможен.'}
                else:
                    return {'intent': 'refund', 'confidence': 0.7,
                            'response': f'Билет {ticket_number} не найден. Проверьте номер.'}
            else:
                return {'intent': 'refund', 'confidence': 0.5,
                        'response': 'Пожалуйста, введите 10-значный номер билета.'}

        if step == 1:
            if msg in ['да', 'конечно', 'давай', 'подтверждаю']:
                ticket_number = state.get('ticket_number')
                update_ticket_status(ticket_number, 'refunded')
                del self.states[session_id]
                return {'intent': 'refund', 'confidence': 0.95,
                        'response': f'✅ Возврат билета {ticket_number} оформлен. Деньги поступят в течение 5–10 дней.'}
            elif msg in ['нет', 'отмена', 'не надо']:
                del self.states[session_id]
                return {'intent': 'refund', 'confidence': 0.9,
                        'response': 'Возврат отменён. Если передумаете, напишите снова.'}
            else:
                return {'intent': 'refund', 'confidence': 0.6,
                        'response': 'Пожалуйста, ответьте "Да" или "Нет".'}

        del self.states[session_id]
        return {'intent': 'refund', 'confidence': 0.5,
                'response': 'Ошибка. Напишите "Вернуть билет" и номер.'}

    # ----- Уточнение расписания -----
    def _handle_schedule_dialog(self, msg: str, session_id: str):
        if 'шереметьево' in msg:
            del self.states[session_id]
            return {'intent': 'schedule', 'confidence': 0.9,
                    'response': 'До Шереметьево: каждые 30 мин, в пути 35 мин.'}
        if 'домодедово' in msg:
            del self.states[session_id]
            return {'intent': 'schedule', 'confidence': 0.9,
                    'response': 'До Домодедово: каждые 30 мин, в пути 45 мин.'}
        return {'intent': 'schedule', 'confidence': 0.7,
                'response': 'Уточните маршрут: "Шереметьево" или "Домодедово".'}

    # ----- Неизвестный запрос -----
    def _handle_unknown_dialog(self, msg: str, session_id: str):
        state = self.states.get(session_id, {})
        step = state.get('step', 0)

        if step == 0:
            self.states[session_id]['step'] = 1
            return {'intent': 'unknown', 'confidence': 0.5,
                    'response': 'Извините, не понял. Вы спрашиваете о расписании, ценах или возврате билетов?'}
        else:
            del self.states[session_id]
            return self.process_message(msg, session_id)

    # ----- Форматирование билетов -----
    def _show_tickets_and_ask_action(self, tickets):
        if not tickets:
            return {'intent': 'find_ticket', 'confidence': 0.9,
                    'response': 'Билеты не найдены. Проверьте правильность ввода.'}
        response = "🎫 Найдены ваши билеты:\n\n"
        for t in tickets:
            response += f"• Номер: {t[1]}\n  Маршрут: {t[5]}\n  Дата: {t[6]}, отправление: {t[7]}\n  Статус: {t[8]}\n\n"
        response += "Если хотите вернуть один из билетов, напишите его номер (10 цифр). Если нет – ответьте «нет»."
        return {'intent': 'find_ticket', 'confidence': 0.9, 'response': response}

    def reset_session(self, session_id: str):
        if session_id in self.states:
            del self.states[session_id]

chatbot = ChatBot()