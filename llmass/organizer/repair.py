from typing import List
import time


def repair_mailbox(bot, folder: str = 'INBOX', force: bool = False, dry_run: bool = False):
    """
    Naprawia corruption UIDs w skrzynce IMAP poprzez bezpieczne przenoszenie emaili.

    Delegowana implementacja wyodrębniona z EmailOrganizer.repair_mailbox.
    Parametr `bot` powinien posiadać: imap, create_folder(), subscribe_folder(), _encode_mailbox().
    """
    print("🔧 NAPRAWA CORRUPTION SKRZYNKI IMAP")
    print("=" * 50)
    print("")

    if not force and not dry_run:
        print("⚠️  UWAGA: Ta operacja przeniesie wszystkie emaile do folderu tymczasowego")
        print("   i z powrotem w celu regeneracji UIDs. Jest to bezpieczne ale:")
        print("   - Zajmie trochę czasu")
        print("   - Może zmienić kolejność emaili")
        print("   - Zaleca się backup skrzynki przed naprawą")
        print("")

        confirm = input("Czy chcesz kontynuować? (tak/nie): ").lower().strip()
        if confirm not in ['tak', 'yes', 'y', 't']:
            print("❌ Naprawa anulowana przez użytkownika")
            return
        print("")

    try:
        # Krok 1: Sprawdź czy folder istnieje
        print(f"📂 Sprawdzam folder: {folder}")
        client = getattr(bot, 'client', None)
        result, data = (client.safe_select(folder, readonly=True) if client else bot.imap.select(folder, readonly=True))
        if result != 'OK':
            print(f"❌ Nie można otworzyć folderu {folder}")
            return

        # Krok 2: Sprawdź corruption
        print("🔍 Sprawdzam corruption UIDs...")
        result, data = (client.safe_uid('SEARCH', None, 'ALL') if client else bot.imap.uid('SEARCH', None, 'ALL'))
        if result == 'OK' and data and data[0]:
            uids = data[0].split()[:10]  # Test pierwszych 10 UIDs
            corrupted_count = 0

            for uid in uids:
                result, test_data = (client.safe_uid('FETCH', uid, '(FLAGS)') if client else bot.imap.uid('FETCH', uid, '(FLAGS)'))
                if result != 'OK' or not test_data or test_data == [None]:
                    corrupted_count += 1

            corruption_ratio = corrupted_count / len(uids) if uids else 0
            print(f"   Corruption ratio: {corruption_ratio:.1%} ({corrupted_count}/{len(uids)} UIDs)")

            if corruption_ratio < 0.5:
                print("✅ Skrzynka nie wymaga naprawy (corruption < 50%)")
                return

        # Krok 3: Utwórz folder tymczasowy
        repair_folder = f"{folder}_REPAIR_TEMP_{int(time.time())}"
        print(f"📁 Tworzę folder tymczasowy: {repair_folder}")

        if not dry_run:
            try:
                bot.create_folder(repair_folder)
            except Exception as e:
                print(f"❌ Nie można utworzyć folderu tymczasowego: {e}")
                return
        else:
            if getattr(bot, 'verbose', False):
                print("🧪 [DRY-RUN] Utworzyłbym folder tymczasowy")

        # Krok 4: Przenieś wszystkie emaile sekwencyjnie
        print(f"🔄 Przenoszę emaile z {folder} do {repair_folder}...")

        # Przełącz na tryb read-write
        result, data = (client.safe_select(folder, readonly=False) if client else bot.imap.select(folder, readonly=False))
        if result != 'OK':
            print(f"❌ Nie można otworzyć {folder} w trybie read-write")
            return

        # Użyj sekwencyjnych numerów (nie UIDs)
        if client:
            result, data = client.safe_search(None, 'ALL')
        else:
            result, data = bot.imap.search(None, 'ALL')
        if result == 'OK' and data and data[0]:
            seq_nums = data[0].split()
            total_emails = len(seq_nums)
            print(f"   Znaleziono {total_emails} emaili do przeniesienia")

            if dry_run:
                if getattr(bot, 'verbose', False):
                    print(f"🧪 [DRY-RUN] Przeniosłbym {total_emails} emaili")
            else:
                # Przenoś po batch (50 naraz)
                batch_size = 50
                moved_count = 0

                for i in range(0, len(seq_nums), batch_size):
                    batch = seq_nums[i:i+batch_size]
                    batch_str = ','.join([num.decode() if isinstance(num, bytes) else str(num) for num in batch])

                    try:
                        # COPY + STORE \Deleted + EXPUNGE
                        mailbox_encoded = bot._encode_mailbox(repair_folder)
                        if client:
                            client.safe_copy(batch_str, mailbox_encoded)
                            client.safe_store(batch_str, '+FLAGS', '\\Deleted')
                            client.safe_expunge()
                        else:
                            bot.imap.copy(batch_str, mailbox_encoded)
                            bot.imap.store(batch_str, '+FLAGS', '\\Deleted')
                            bot.imap.expunge()

                        moved_count += len(batch)
                        print(f"   Przeniesiono: {moved_count}/{total_emails} emaili", end='\r')

                    except Exception as e:
                        print(f"\n❌ Błąd podczas przenoszenia batch {i//batch_size + 1}: {e}")
                        break

                print(f"\n✅ Przeniesiono {moved_count} emaili do folderu tymczasowego")

        # Krok 5: Przenieś z powrotem
        print(f"🔄 Przenoszę emaile z powrotem z {repair_folder} do {folder}...")

        if not dry_run:
            result, data = (client.safe_select(repair_folder, readonly=False) if client else bot.imap.select(repair_folder, readonly=False))
            if result == 'OK':
                if client:
                    result, data = client.safe_search(None, 'ALL')
                else:
                    result, data = bot.imap.search(None, 'ALL')
                if result == 'OK' and data and data[0]:
                    seq_nums = data[0].split()

                    # Przenoś z powrotem po batch
                    moved_back = 0
                    batch_size = 50
                    for i in range(0, len(seq_nums), batch_size):
                        batch = seq_nums[i:i+batch_size]
                        batch_str = ','.join([num.decode() if isinstance(num, bytes) else str(num) for num in batch])

                        try:
                            mailbox_encoded = bot._encode_mailbox(folder)
                            if client:
                                client.safe_copy(batch_str, mailbox_encoded)
                                client.safe_store(batch_str, '+FLAGS', '\\Deleted')
                                client.safe_expunge()
                            else:
                                bot.imap.copy(batch_str, mailbox_encoded)
                                bot.imap.store(batch_str, '+FLAGS', '\\Deleted')
                                bot.imap.expunge()

                            moved_back += len(batch)
                            print(f"   Przywrócono: {moved_back}/{len(seq_nums)} emaili", end='\r')

                        except Exception as e:
                            print(f"\n❌ Błąd podczas przywracania batch {i//batch_size + 1}: {e}")
                            break

                    print(f"\n✅ Przywrócono {moved_back} emaili do {folder}")
        else:
            if getattr(bot, 'verbose', False):
                print("🧪 [DRY-RUN] Przywróciłbym wszystkie emaile")

        # Krok 6: Usuń folder tymczasowy
        print(f"🗑️  Usuwam folder tymczasowy: {repair_folder}")
        if not dry_run:
            try:
                if client:
                    client.safe_select()
                    client.safe_delete(bot._encode_mailbox(repair_folder))
                else:
                    bot.imap.select()  # Deselect current folder
                    bot.imap.delete(bot._encode_mailbox(repair_folder))
                print("✅ Folder tymczasowy usunięty")
            except Exception as e:
                print(f"⚠️  Nie można usunąć folderu tymczasowego: {e}")
                print(f"   Możesz usunąć go ręcznie: {repair_folder}")
        else:
            if getattr(bot, 'verbose', False):
                print("🧪 [DRY-RUN] Usunąłbym folder tymczasowy")

        # Krok 7: Weryfikacja
        print("🔍 Weryfikuję naprawę...")
        if not dry_run:
            result, data = (client.safe_select(folder, readonly=True) if client else bot.imap.select(folder, readonly=True))
            if result == 'OK':
                result, data = (client.safe_uid('SEARCH', None, 'ALL') if client else bot.imap.uid('SEARCH', None, 'ALL'))
                if result == 'OK' and data and data[0]:
                    uids = data[0].split()[:10]
                    working_count = 0

                    for uid in uids:
                        result, test_data = (client.safe_uid('FETCH', uid, '(FLAGS)') if client else bot.imap.uid('FETCH', uid, '(FLAGS)'))
                        if result == 'OK' and test_data and test_data != [None]:
                            working_count += 1

                    success_ratio = working_count / len(uids) if uids else 0
                    print(f"   UIDs working: {success_ratio:.1%} ({working_count}/{len(uids)})")

                    if success_ratio > 0.9:
                        print("🎉 NAPRAWA ZAKOŃCZONA POMYŚLNIE!")
                        print("   Skrzynka powinna teraz działać normalnie z llmass clean")
                    else:
                        print("⚠️  Naprawa częściowo udana. Możliwe że potrzebne są dodatkowe kroki.")

    except Exception as e:
        print(f"❌ Błąd podczas naprawy: {e}")
        import traceback
        traceback.print_exc()

    print("")
    print("=" * 50)
    print("🔧 NAPRAWA ZAKOŃCZONA")
