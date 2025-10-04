#!/usr/bin/env python3
"""
IMAP Utils - Narzędzia pomocnicze i przykłady użycia IMAPClient
"""

from imap_client import IMAPClient, IMAPStrategy, IMAPCorruptionLevel
import os
from dotenv import load_dotenv

def handle_corrupted_mailbox_example():
    """Przykład obsługi skrzynki z corruption"""
    load_dotenv()
    
    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    server = os.getenv('IMAP_SERVER')
    
    if not email or not password:
        print("❌ Brak konfiguracji EMAIL_ADDRESS i EMAIL_PASSWORD w .env")
        return
    
    print("🔧 PRZYKŁAD OBSŁUGI CORRUPTION SKRZYNKI")
    print("=" * 50)
    
    # Inicjalizacja klienta
    client = IMAPClient(email, password, server)
    
    try:
        # Krok 1: Połączenie
        if not client.connect():
            print("❌ Nie można połączyć się z serwerem")
            return
        
        print("✅ Połączenie nawiązane")
        
        # Krok 2: Test połączenia i diagnostyka
        test_results = client.test_connection()
        print(f"\n📊 Wyniki testu połączenia:")
        print(f"   Serwer: {test_results['server']}")
        print(f"   Foldery dostępne: {len(test_results['folders_accessible'])}")
        print(f"   Corruption wykryty: {'✅' if test_results['corruption_detected'] else '❌'}")
        
        # Krok 3: Diagnoza corruption dla INBOX
        print(f"\n🔍 Diagnoza corruption INBOX...")
        corruption_level = client.diagnose_corruption('INBOX', sample_size=10)
        print(f"   Poziom corruption: {corruption_level.name}")
        
        # Krok 4: Wybór strategii
        strategy = client.select_strategy(corruption_level)
        print(f"   Zalecana strategia: {strategy.value}")
        
        # Krok 5: Bezpieczne pobieranie emaili (test różnych limitów)
        print(f"\n📥 Pobieranie emaili bezpieczną metodą...")
        
        # Test z małym limitem (jak teraz)
        emails = client.fetch_emails_safe('INBOX', limit=10)
        print(f"   Limit 10: Pobrano {len(emails)} emaili")
        
        # Test z większym limitem (jak llmass clean bez limitu)
        print(f"\n📥 Test większego limitu...")
        try:
            all_emails = client.fetch_emails_safe('INBOX', limit=100)
            print(f"   Limit 100: Pobrano {len(all_emails)} emaili")
        except Exception as e:
            print(f"   ❌ Błąd przy limit 100: {e}")
        
        # Test bez limitu (jak prawdziwy llmass clean)
        print(f"\n📥 Test bez limitu...")
        try:
            unlimited_emails = client.fetch_emails_safe('INBOX', limit=None)
            print(f"   Bez limitu: Pobrano {len(unlimited_emails)} emaili")
        except Exception as e:
            print(f"   ❌ Błąd bez limitu: {e}")
            # To może wywołać corruption!
        
        # Krok 6: Wyświetl przykładowe dane
        for i, email_data in enumerate(emails[:3]):
            print(f"\n📧 Email {i+1}:")
            print(f"   From: {email_data.get('from', 'N/A')[:50]}...")
            print(f"   Subject: {email_data.get('subject', 'N/A')[:50]}...")
            print(f"   ID: {email_data.get('id')}")
        
        # Krok 7: Jeśli corruption jest poważny, zaproponuj naprawę
        if corruption_level in [IMAPCorruptionLevel.SEVERE, IMAPCorruptionLevel.CRITICAL]:
            print(f"\n🚨 WYKRYTO POWAŻNĄ CORRUPTION!")
            print(f"   Rekomendacja: Użyj llmass repair lub repair_corruption_simple()")
            
            # Test naprawy (dry-run)
            print(f"\n🧪 Test naprawy (dry-run)...")
            success = client.repair_corruption_simple('INBOX', dry_run=True)
            print(f"   Naprawa możliwa: {'✅' if success else '❌'}")
    
    except Exception as e:
        print(f"❌ Błąd: {e}")
    
    finally:
        client.disconnect()
        print(f"\n👋 Rozłączono")

def compare_strategies_example():
    """Porównanie różnych strategii pobierania emaili"""
    load_dotenv()
    
    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    server = os.getenv('IMAP_SERVER')
    
    if not email or not password:
        return
    
    print("⚖️  PORÓWNANIE STRATEGII IMAP")
    print("=" * 40)
    
    client = IMAPClient(email, password, server)
    
    if not client.connect():
        return
    
    try:
        strategies = [
            IMAPStrategy.STANDARD,
            IMAPStrategy.SEQUENCE, 
            IMAPStrategy.BATCH,
            IMAPStrategy.RECOVERY,
            IMAPStrategy.SAFE
        ]
        
        results = {}
        
        for strategy in strategies:
            print(f"\n🔄 Test strategii: {strategy.value}")
            client.strategy = strategy
            
            import time
            start_time = time.time()
            
            try:
                emails = client.fetch_emails_safe('INBOX', limit=5)
                elapsed = time.time() - start_time
                
                results[strategy] = {
                    'success': True,
                    'count': len(emails),
                    'time': elapsed,
                    'error': None
                }
                
                print(f"   ✅ Pobrano {len(emails)} emaili w {elapsed:.2f}s")
                
            except Exception as e:
                results[strategy] = {
                    'success': False,
                    'count': 0,
                    'time': time.time() - start_time,
                    'error': str(e)
                }
                print(f"   ❌ Błąd: {e}")
        
        # Podsumowanie
        print(f"\n📊 PODSUMOWANIE:")
        for strategy, result in results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {strategy.value:10} | {result['count']:2} emaili | {result['time']:.2f}s")
    
    finally:
        client.disconnect()

def folder_info_example():
    """Przykład pobierania informacji o folderach"""
    load_dotenv()
    
    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD')
    server = os.getenv('IMAP_SERVER')
    
    if not email or not password:
        return
    
    print("📁 INFORMACJE O FOLDERACH")
    print("=" * 30)
    
    client = IMAPClient(email, password, server)
    
    if not client.connect():
        return
    
    try:
        # Lista folderów do sprawdzenia
        folders_to_check = ['INBOX', 'INBOX.Sent', 'INBOX.Spam', 'INBOX.Drafts']
        
        for folder in folders_to_check:
            print(f"\n📂 Folder: {folder}")
            
            info = client.get_folder_info(folder)
            
            if info['exists']:
                print(f"   ✅ Istnieje")
                print(f"   📧 Emaile: {info['email_count']}")
                print(f"   🔍 Corruption: {info['corruption_level'].name}")
                print(f"   ⚙️  Strategia: {info['strategy_recommended'].value}")
            else:
                print(f"   ❌ Nie istnieje lub niedostępny")
    
    finally:
        client.disconnect()

def emergency_recovery_example():
    """Przykład awaryjnego odzyskiwania z całkowicie uszkodzonej skrzynki"""
    load_dotenv()
    
    email = os.getenv('EMAIL_ADDRESS')
    password = os.getenv('EMAIL_PASSWORD') 
    server = os.getenv('IMAP_SERVER')
    
    if not email or not password:
        return
    
    print("🆘 AWARYJNE ODZYSKIWANIE DANYCH")
    print("=" * 35)
    
    client = IMAPClient(email, password, server)
    
    if not client.connect():
        return
    
    try:
        # Wymuś bezpieczny tryb
        client.strategy = IMAPStrategy.SAFE
        client.corruption_level = IMAPCorruptionLevel.CRITICAL
        
        print("🔄 Próba odzyskania emaili w trybie awaryjnym...")
        
        # Pobierz choć kilka emaili
        emails = client._fetch_safe_mode(limit=20)
        
        if emails:
            print(f"✅ Odzyskano {len(emails)} emaili")
            
            # Zapisz do pliku jako backup
            import json
            backup_file = f"emergency_backup_{int(time.time())}.json"
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(emails, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Backup zapisany do: {backup_file}")
            
            # Pokaż przykładowe odzyskane dane
            for i, email_data in enumerate(emails[:3]):
                print(f"\n📧 Odzyskany email {i+1}:")
                print(f"   From: {email_data.get('from', 'N/A')}")
                print(f"   Subject: {email_data.get('subject', 'N/A')}")
                print(f"   Date: {email_data.get('date', 'N/A')}")
        else:
            print("❌ Nie udało się odzyskać żadnych emaili")
            print("💡 Spróbuj:")
            print("   1. Użyć klienta email (Thunderbird) do naprawy")
            print("   2. Skontaktować się z dostawcą email")
            print("   3. Przywrócić z backupu")
    
    finally:
        client.disconnect()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        
        if example == "corruption":
            handle_corrupted_mailbox_example()
        elif example == "strategies":
            compare_strategies_example()
        elif example == "folders":
            folder_info_example()
        elif example == "emergency":
            emergency_recovery_example()
        else:
            print("Dostępne przykłady:")
            print("  python imap_utils.py corruption   - Obsługa corruption")
            print("  python imap_utils.py strategies   - Porównanie strategii")
            print("  python imap_utils.py folders      - Info o folderach")
            print("  python imap_utils.py emergency    - Awaryjne odzyskiwanie")
    else:
        print("🔧 IMAP Utils - Przykłady użycia")
        print("\nDostępne przykłady:")
        print("  python imap_utils.py corruption   - Obsługa corruption")
        print("  python imap_utils.py strategies   - Porównanie strategii")
        print("  python imap_utils.py folders      - Info o folderach")
        print("  python imap_utils.py emergency    - Awaryjne odzyskiwanie")
