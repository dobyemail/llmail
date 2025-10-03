#!/usr/bin/env python3
"""
Generator testowych emaili dla środowiska testowego
"""

import smtplib
import random
import time
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from faker import Faker
import lorem
from datetime import datetime, timedelta
from typing import List, Dict
import json
from dotenv import load_dotenv

class TestEmailGenerator:
    def __init__(self, smtp_host='localhost', smtp_port=1025):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.fake = Faker(['pl_PL', 'en_US'])
        
        # Kategorie emaili
        self.categories = {
            'work': {
                'subjects': [
                    'Meeting tomorrow at {time}',
                    'Project {project} update',
                    'Deadline reminder: {project}',
                    'Team lunch on {day}',
                    'Quarterly report - {quarter}',
                    'New task assigned: {task}',
                    'Budget approval needed',
                    'Conference call at {time}'
                ],
                'senders': ['boss@company.com', 'hr@company.com', 'team@company.com', 
                           'project@company.com', 'admin@company.com'],
                'weight': 0.25
            },
            'newsletters': {
                'subjects': [
                    'Weekly Newsletter - {date}',
                    'Tech News Digest #{number}',
                    'Your monthly update from {company}',
                    'Industry insights - {topic}',
                    'Breaking: {news}',
                    'Top 10 {category} this week'
                ],
                'senders': ['newsletter@techblog.com', 'updates@medium.com', 
                           'news@hackernews.com', 'digest@dev.to'],
                'weight': 0.20
            },
            'shopping': {
                'subjects': [
                    'Order #{order_id} confirmed',
                    'Your package is on the way!',
                    'Flash sale: {discount}% off everything!',
                    'Items in your cart are waiting',
                    'New arrivals in {category}',
                    'Weekend deals - save up to {discount}%'
                ],
                'senders': ['orders@amazon.com', 'shop@ebay.com', 'deals@aliexpress.com',
                           'store@zalando.pl', 'sale@allegro.pl'],
                'weight': 0.15
            },
            'social': {
                'subjects': [
                    '{name} sent you a message',
                    'You have {count} new notifications',
                    '{name} tagged you in a photo',
                    'Friend request from {name}',
                    'Reminder: {event} is tomorrow',
                    '{name} commented on your post'
                ],
                'senders': ['notifications@facebook.com', 'alerts@linkedin.com',
                           'updates@twitter.com', 'social@instagram.com'],
                'weight': 0.15
            },
            'banking': {
                'subjects': [
                    'Transaction confirmation - {amount} PLN',
                    'Your statement is ready',
                    'Security alert on your account',
                    'Payment received: {amount} PLN',
                    'Card payment authorization',
                    'Monthly account summary'
                ],
                'senders': ['noreply@bank.com', 'alerts@paypal.com', 'security@bank.pl'],
                'weight': 0.10
            },
            'personal': {
                'subjects': [
                    'Re: {topic}',
                    'Quick question about {topic}',
                    'Thanks for yesterday!',
                    'Let\'s catch up soon',
                    'Happy birthday!',
                    'Invitation: {event}'
                ],
                'senders': [],  # Będą generowane losowo
                'weight': 0.15
            }
        }
        
        # Wzorce spamu
        self.spam_patterns = [
            {
                'subject': '🎉 Congratulations! You won ${amount}!!!',
                'sender': 'winner@lottery{number}.com',
                'body': 'You are our lucky winner! Click here immediately to claim your prize of ${amount}! Act now! This offer expires in 24 hours!!!'
            },
            {
                'subject': 'VIAGRA - 80% OFF - LIMITED TIME',
                'sender': 'pharmacy{number}@cheapmeds.net',
                'body': 'Best prices on VIAGRA, CIALIS and more! No prescription needed! Fast discrete shipping! Order now and save!!!'
            },
            {
                'subject': 'Nigerian Prince needs your help',
                'sender': 'prince.{name}@nigeria.gov',
                'body': 'Dear friend, I am Prince {name} and I need your help to transfer ${amount} million out of my country. You will receive 40% commission...'
            },
            {
                'subject': 'Make $5000 per week working from home!',
                'sender': 'easy.money@workfromhome{number}.biz',
                'body': 'Discover this one weird trick to make money from home! No experience needed! Start earning today!'
            },
            {
                'subject': 'Your account will be suspended!!!',
                'sender': 'security@{company}-verify.com',
                'body': 'Your account will be suspended unless you verify your information immediately. Click here to verify your account now!'
            },
            {
                'subject': 'Hot singles in your area want to meet!',
                'sender': 'dating{number}@meetlocals.net',
                'body': 'View photos of singles near you! No credit card required! Sign up free today!'
            }
        ]
        
        self.generated_emails = []
        
    def generate_normal_email(self, category: str) -> Dict:
        """Generuje normalny email z określonej kategorii"""
        cat_data = self.categories[category]
        
        # Wybierz losowy temat i uzupełnij placeholdery
        subject_template = random.choice(cat_data['subjects'])
        subject = subject_template.format(
            time=self.fake.time(),
            project=self.fake.catch_phrase(),
            day=self.fake.day_of_week(),
            quarter=f"Q{random.randint(1,4)}",
            task=self.fake.bs(),
            date=self.fake.date(),
            number=random.randint(100, 999),
            company=self.fake.company(),
            topic=self.fake.word(),
            news=self.fake.sentence(nb_words=4),
            category=self.fake.word(),
            order_id=self.fake.uuid4()[:8],
            discount=random.choice([10, 20, 30, 50, 70]),
            name=self.fake.first_name(),
            count=random.randint(1, 20),
            event=self.fake.catch_phrase(),
            amount=random.randint(10, 5000)
        )
        
        # Wybierz nadawcę
        if cat_data['senders']:
            sender = random.choice(cat_data['senders'])
        else:
            # Dla osobistych - generuj losowy adres
            sender = self.fake.email()
        
        # Generuj treść
        if category == 'work':
            body = self._generate_work_email_body()
        elif category == 'newsletters':
            body = self._generate_newsletter_body()
        elif category == 'shopping':
            body = self._generate_shopping_body()
        elif category == 'banking':
            body = self._generate_banking_body()
        elif category == 'social':
            body = self._generate_social_body()
        else:
            body = self._generate_personal_body()
        
        return {
            'subject': subject,
            'sender': sender,
            'recipient': 'test@localhost',
            'body': body,
            'category': category,
            'is_spam': False
        }
    
    def generate_spam_email(self) -> Dict:
        """Generuje spam email"""
        spam = random.choice(self.spam_patterns).copy()
        
        # Uzupełnij placeholdery
        spam['subject'] = spam['subject'].replace('{amount}', str(random.randint(1000, 1000000)))
        spam['sender'] = spam['sender'].replace('{number}', str(random.randint(100, 999)))
        spam['sender'] = spam['sender'].replace('{name}', self.fake.last_name())
        spam['sender'] = spam['sender'].replace('{company}', random.choice(['paypal', 'amazon', 'google', 'microsoft']))
        
        spam['body'] = spam['body'].replace('{amount}', str(random.randint(1000, 1000000)))
        spam['body'] = spam['body'].replace('{name}', self.fake.name())
        
        return {
            'subject': spam['subject'],
            'sender': spam['sender'],
            'recipient': 'test@localhost',
            'body': spam['body'],
            'category': 'spam',
            'is_spam': True
        }
    
    def _generate_work_email_body(self) -> str:
        """Generuje treść emaila służbowego"""
        templates = [
            """Hi Team,

{intro}

Key points:
- {point1}
- {point2}
- {point3}

{action}

Best regards,
{name}
{position}""",
            """Dear colleagues,

{intro}

Please note that {announcement}.

{details}

Thanks,
{name}"""
        ]
        
        template = random.choice(templates)
        return template.format(
            intro=self.fake.paragraph(nb_sentences=2),
            point1=self.fake.sentence(),
            point2=self.fake.sentence(),
            point3=self.fake.sentence(),
            action=f"Please {self.fake.bs()} by {self.fake.date()}",
            name=self.fake.name(),
            position=self.fake.job(),
            announcement=self.fake.sentence(),
            details=self.fake.paragraph(nb_sentences=3)
        )
    
    def _generate_newsletter_body(self) -> str:
        """Generuje treść newslettera"""
        articles = []
        for i in range(random.randint(3, 5)):
            articles.append(f"""
📰 {self.fake.sentence()}
{self.fake.paragraph(nb_sentences=2)}
Read more: {self.fake.url()}
""")
        
        return f"""This week's highlights:

{''.join(articles)}

---
Unsubscribe | Update preferences | View in browser"""
    
    def _generate_shopping_body(self) -> str:
        """Generuje treść emaila zakupowego"""
        items = []
        for i in range(random.randint(1, 3)):
            items.append(f"• {self.fake.catch_phrase()} - {random.randint(10, 500)} PLN")
        
        return f"""Thank you for your order!

Order details:
{chr(10).join(items)}

Total: {random.randint(50, 1000)} PLN

Estimated delivery: {(datetime.now() + timedelta(days=random.randint(2, 7))).strftime('%Y-%m-%d')}

Track your package: {self.fake.url()}"""
    
    def _generate_banking_body(self) -> str:
        """Generuje treść emaila bankowego"""
        return f"""Dear Customer,

{self.fake.paragraph(nb_sentences=2)}

Transaction details:
Date: {self.fake.date_time()}
Amount: {random.randint(10, 5000)} PLN
Reference: {self.fake.uuid4()[:12].upper()}
Status: Completed

If you didn't make this transaction, please contact us immediately.

Best regards,
Customer Service Team"""
    
    def _generate_social_body(self) -> str:
        """Generuje treść emaila społecznościowego"""
        return f"""{self.fake.name()} {random.choice(['liked', 'commented on', 'shared'])} your {random.choice(['post', 'photo', 'video'])}.

"{self.fake.sentence()}"

See more activity on your profile: {self.fake.url()}

---
You're receiving this because you're subscribed to notifications."""
    
    def _generate_personal_body(self) -> str:
        """Generuje treść emaila osobistego"""
        return f"""Hey!

{self.fake.paragraph(nb_sentences=3)}

{self.fake.paragraph(nb_sentences=2)}

{random.choice(['Talk soon', 'Cheers', 'Best', 'Take care'])},
{self.fake.first_name()}"""
    
    def send_email(self, email_data: Dict):
        """Wysyła email przez SMTP"""
        msg = MIMEMultipart()
        msg['From'] = email_data['sender']
        msg['To'] = email_data['recipient']
        msg['Subject'] = email_data['subject']
        msg.attach(MIMEText(email_data['body'], 'plain'))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.send_message(msg)
                print(f"✉️  Sent: [{email_data['category']}] {email_data['subject'][:50]}")
                return True
        except Exception as e:
            print(f"❌ Failed to send: {e}")
            return False
    
    def generate_batch(self, num_emails: int, spam_ratio: float = 0.2):
        """Generuje partię emaili"""
        print(f"\n🎲 Generowanie {num_emails} emaili (spam: {int(spam_ratio*100)}%)...")
        
        num_spam = int(num_emails * spam_ratio)
        num_normal = num_emails - num_spam
        
        # Generuj normalne emaile
        for i in range(num_normal):
            # Wybierz kategorię z wagami
            category = self._weighted_choice()
            email = self.generate_normal_email(category)
            self.generated_emails.append(email)
        
        # Generuj spam
        for i in range(num_spam):
            email = self.generate_spam_email()
            self.generated_emails.append(email)
        
        # Wymieszaj kolejność
        random.shuffle(self.generated_emails)
        
        # Zapisz metadane
        self.save_metadata()
        
        print(f"✅ Wygenerowano {len(self.generated_emails)} emaili")
        
        # Statystyki
        stats = {}
        for email in self.generated_emails:
            cat = email['category']
            stats[cat] = stats.get(cat, 0) + 1
        
        print("\n📊 Statystyki:")
        for cat, count in sorted(stats.items()):
            print(f"   {cat}: {count} emaili")
    
    def _weighted_choice(self) -> str:
        """Wybiera kategorię z wagami"""
        categories = []
        weights = []
        for cat, data in self.categories.items():
            categories.append(cat)
            weights.append(data['weight'])
        
        return random.choices(categories, weights=weights)[0]
    
    def send_all_emails(self, delay: float = 0.1):
        """Wysyła wszystkie wygenerowane emaile"""
        print(f"\n📤 Wysyłanie {len(self.generated_emails)} emaili...")
        
        sent = 0
        failed = 0
        
        for i, email in enumerate(self.generated_emails, 1):
            print(f"[{i}/{len(self.generated_emails)}] ", end='')
            if self.send_email(email):
                sent += 1
            else:
                failed += 1
            
            time.sleep(delay)  # Małe opóźnienie między emailami
        
        print(f"\n✅ Wysłano: {sent}, ❌ Błędy: {failed}")
        return sent, failed
    
    def save_metadata(self, filename: str = 'test_emails_metadata.json'):
        """Zapisuje metadane o wygenerowanych emailach"""
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'total_emails': len(self.generated_emails),
            'categories': {},
            'emails': []
        }
        
        for email in self.generated_emails:
            cat = email['category']
            if cat not in metadata['categories']:
                metadata['categories'][cat] = 0
            metadata['categories'][cat] += 1
            
            metadata['emails'].append({
                'subject': email['subject'],
                'sender': email['sender'],
                'category': email['category'],
                'is_spam': email['is_spam']
            })
        
        with open(filename, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"📝 Metadane zapisane do {filename}")

def main():
    """Główna funkcja"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generator testowych emaili')
    parser.add_argument('--host', default='localhost', help='SMTP host')
    parser.add_argument('--port', type=int, default=1025, help='SMTP port')
    parser.add_argument('--count', type=int, default=50, help='Liczba emaili do wygenerowania')
    parser.add_argument('--spam-ratio', type=float, default=0.2, help='Procent spamu (0.0-1.0)')
    parser.add_argument('--delay', type=float, default=0.1, help='Opóźnienie między emailami (s)')
    parser.add_argument('--no-send', action='store_true', help='Tylko generuj, nie wysyłaj')
    
    args = parser.parse_args()

    # Załaduj zmienne środowiskowe z .env (jeśli istnieje)
    load_dotenv()
    
    # Użyj zmiennych środowiskowych jeśli są dostępne
    smtp_host = os.environ.get('SMTP_HOST', args.host)
    smtp_port = int(os.environ.get('SMTP_PORT', args.port))
    num_emails = int(os.environ.get('NUM_EMAILS', args.count))
    spam_ratio = float(os.environ.get('SPAM_RATIO', args.spam_ratio))
    
    print("="*50)
    print("📧 TEST EMAIL GENERATOR")
    print("="*50)
    print(f"SMTP Server: {smtp_host}:{smtp_port}")
    print(f"Emails to generate: {num_emails}")
    print(f"Spam ratio: {spam_ratio*100}%")
    print("="*50)
    
    # Stwórz generator
    generator = TestEmailGenerator(smtp_host, smtp_port)
    
    # Generuj emaile
    generator.generate_batch(num_emails, spam_ratio)
    
    # Wyślij emaile (chyba że --no-send)
    if not args.no_send:
        generator.send_all_emails(delay=args.delay)
    else:
        print("\n⏭️  Pomijam wysyłanie (--no-send)")
    
    print("\n✅ Zakończono!")

if __name__ == "__main__":
    main()