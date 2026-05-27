"""
Модуль автоматической обработки входящих писем
"""

import imaplib
import email
import re
import logging
from email.header import decode_header
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import schedule
import time

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорт модуля БД
from database import save_email, get_unprocessed_emails, mark_email_processed

# ==================== Конфигурация почтового сервера ====================
# Для демонстрации используем тестовые данные
# В реальном проекте настройки берутся из переменных окружения

EMAIL_CONFIG = {
    'imap_server': 'imap.gmail.com',  # Замените на ваш сервер
    'email_user': 'support@aeroexpress.ru',
    'email_password': 'your_password_here',
    'check_interval_minutes': 5
}

# ==================== Классификатор писем ====================

class EmailClassifier:
    """Классификация писем по тематике"""
    
    # Категории и их ключевые слова
    CATEGORIES = {
        'refund': ['возврат', 'вернуть деньги', 'сдать билет', 'отмена', 'компенсация', 'деньги назад'],
        'schedule': ['расписание', 'отправление', 'прибытие', 'время', 'задержка', 'опоздание', 'поезд'],
        'complaint': ['жалоба', 'претензия', 'недоволен', 'плохо', 'ужасно', 'невозможно', 'проблема'],
        'baggage': ['багаж', 'чемодан', 'ручная кладь', 'вещи', 'потерял', 'пропал'],
        'ticket_purchase': ['билет', 'покупка', 'купить', 'оплата', 'сайт', 'приложение'],
        'general': []
    }
    
    # Отделы назначения
    DEPARTMENT_MAPPING = {
        'refund': 'Финансовый отдел',
        'schedule': 'Информационная служба',
        'complaint': 'Отдел качества',
        'baggage': 'Сервисный центр',
        'ticket_purchase': 'Отдел продаж',
        'general': 'Контакт-центр'
    }
    
    def __init__(self):
        logger.info("Email классификатор инициализирован")
    
    def classify(self, subject: str, body: str) -> Tuple[str, float, str]:
        """
        Классификация письма
        Возвращает: (category, confidence, department)
        """
        text = f"{subject} {body}".lower()
        
        best_category = 'general'
        best_score = 0.0
        
        for category, keywords in self.CATEGORIES.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    # Более длинные ключевые слова дают больше очков
                    score += len(keyword) / 10
            
            if score > best_score:
                best_score = score
                best_category = category
        
        # Нормализация уверенности
        confidence = min(best_score / 2.0, 0.95) if best_score > 0 else 0.3
        
        department = self.DEPARTMENT_MAPPING.get(best_category, 'Контакт-центр')
        
        return best_category, confidence, department
    
    def extract_ticket_number(self, text: str) -> Optional[str]:
        """Извлечение номера билета из текста"""
        match = re.search(r'\b\d{10}\b', text)
        return match.group() if match else None
    
    def extract_contact_info(self, text: str) -> Dict[str, str]:
        """Извлечение контактной информации"""
        info = {}
        
        # Поиск email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            info['email'] = email_match.group()
        
        # Поиск телефона
        phone_match = re.search(r'\+?[78][-\s]?\(?[0-9]{3}\)?[-\s]?[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{2}', text)
        if phone_match:
            info['phone'] = phone_match.group()
        
        return info

# ==================== Обработчик писем ====================

class EmailProcessor:
    """Основной класс обработки писем"""
    
    def __init__(self):
        self.classifier = EmailClassifier()
        self.connection = None
        logger.info("Email процессор инициализирован")
    
    def connect(self) -> bool:
        """Подключение к почтовому серверу"""
        try:
            self.connection = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'])
            self.connection.login(EMAIL_CONFIG['email_user'], EMAIL_CONFIG['email_password'])
            self.connection.select('INBOX')
            logger.info("Подключение к почтовому серверу установлено")
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return False
    
    def disconnect(self):
        """Отключение от почтового сервера"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
            except:
                pass
            self.connection = None
    
    def decode_mime_text(self, text: str, encoding: str = 'utf-8') -> str:
        """Декодирование текста из MIME формата"""
        if text is None:
            return ""
        try:
            decoded_parts = []
            for part in decode_header(text):
                if isinstance(part[0], bytes):
                    charset = part[1] or 'utf-8'
                    try:
                        decoded_parts.append(part[0].decode(charset, errors='ignore'))
                    except:
                        decoded_parts.append(part[0].decode('utf-8', errors='ignore'))
                else:
                    decoded_parts.append(str(part[0]))
            return ' '.join(decoded_parts)
        except:
            return str(text)
    
    def extract_body(self, msg) -> str:
        """Извлечение текстового тела письма"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Берем только text/plain части, не вложения
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
                    except:
                        pass
        else:
            # Не multipart письмо
            try:
                payload = msg.get_payload(decode=True)
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
            except:
                body = str(msg.get_payload())
        
        # Очистка от лишних пробелов и символов
        body = re.sub(r'\s+', ' ', body).strip()
        
        return body
    
    def fetch_unread_emails(self, limit: int = 50) -> List[Dict]:
        """Получение непрочитанных писем"""
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            # Поиск непрочитанных писем
            result, data = self.connection.search(None, 'UNSEEN')
            if result != 'OK':
                return []
            
            email_ids = data[0].split()
            if not email_ids:
                logger.info("Непрочитанных писем нет")
                return []
            
            emails = []
            for email_id in email_ids[:limit]:
                result, msg_data = self.connection.fetch(email_id, '(RFC822)')
                if result != 'OK':
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1])
                
                # Извлечение данных
                subject = self.decode_mime_text(msg.get('Subject', 'Без темы'))
                sender = msg.get('From', '')
                date = msg.get('Date', '')
                body = self.extract_body(msg)
                
                emails.append({
                    'id': email_id.decode() if isinstance(email_id, bytes) else str(email_id),
                    'sender': sender,
                    'subject': subject,
                    'date': date,
                    'body': body
                })
            
            logger.info(f"Получено {len(emails)} новых писем")
            return emails
            
        except Exception as e:
            logger.error(f"Ошибка получения писем: {e}")
            return []
    
    def process_email(self, email_data: Dict) -> Dict:
        """Обработка одного письма"""
        # Классификация
        category, confidence, department = self.classifier.classify(
            email_data['subject'],
            email_data['body']
        )
        
        # Извлечение дополнительной информации
        full_text = f"{email_data['subject']} {email_data['body']}"
        ticket_number = self.classifier.extract_ticket_number(full_text)
        contact_info = self.classifier.extract_contact_info(full_text)
        
        # Сохранение в БД
        email_id = save_email(
            sender=email_data['sender'],
            subject=email_data['subject'],
            body=email_data['body'],
            predicted_intent=category,
            confidence=confidence,
            target_department=department
        )
        
        # Формирование результата
        result = {
            'email_id': email_id,
            'sender': email_data['sender'],
            'subject': email_data['subject'],
            'category': category,
            'confidence': confidence,
            'department': department,
            'ticket_number': ticket_number,
            'contact_info': contact_info,
            'auto_processable': confidence > 0.7
        }
        
        logger.info(f"Письмо обработано: {category} (уверенность: {confidence:.2f})")
        
        return result
    
    def process_all_new_emails(self) -> Dict:
        """Обработка всех новых писем"""
        emails = self.fetch_unread_emails()
        
        if not emails:
            return {'processed': 0, 'classified': 0, 'escalated': 0, 'results': []}
        
        results = []
        for email_data in emails:
            result = self.process_email(email_data)
            results.append(result)
        
        summary = {
            'processed': len(emails),
            'classified': sum(1 for r in results if r['auto_processable']),
            'escalated': sum(1 for r in results if not r['auto_processable']),
            'results': results
        }
        
        logger.info(f"Обработка завершена: {summary}")
        
        return summary
    
    def generate_daily_report(self) -> str:
        """Генерация дневного отчёта по обработанным письмам"""
        unprocessed = get_unprocessed_emails(limit=1000)
        
        if not unprocessed:
            return "📊 Отчёт: За сегодня писем не поступало."
        
        # Подсчёт по категориям
        category_counts = {}
        for email in unprocessed:
            cat = email.get('predicted_intent', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        report = f"📧 Отчёт по обработке писем за {datetime.now().strftime('%d.%m.%Y')}\n\n"
        report += f"Всего обработано: {len(unprocessed)}\n\n"
        report += "По категориям:\n"
        for cat, count in category_counts.items():
            report += f"  • {cat}: {count}\n"
        
        report += "\nАвтоматически обработано: " + str(sum(1 for e in unprocessed if e.get('confidence', 0) > 0.7))
        
        return report

# ==================== Автоматический запуск по расписанию ====================

def scheduled_email_processing():
    """Функция для запуска по расписанию"""
    processor = EmailProcessor()
    try:
        result = processor.process_all_new_emails()
        if result['processed'] > 0:
            logger.info(f"По расписанию обработано {result['processed']} писем")
    except Exception as e:
        logger.error(f"Ошибка в scheduled_email_processing: {e}")
    finally:
        processor.disconnect()

def run_scheduler():
    """Запуск планировщика"""
    schedule.every(EMAIL_CONFIG['check_interval_minutes']).minutes.do(scheduled_email_processing)
    logger.info(f"Планировщик запущен (интервал: {EMAIL_CONFIG['check_interval_minutes']} мин)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# ==================== Использование ====================

if __name__ == "__main__":
    # Для ручного запуска
    processor = EmailProcessor()
    try:
        result = processor.process_all_new_emails()
        print(result)
    finally:
        processor.disconnect()