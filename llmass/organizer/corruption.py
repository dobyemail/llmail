from typing import List


def check_and_handle_corruption(ctx, email_ids: List[bytes]) -> float:
    """
    Checks UID corruption using the first up-to-10 IDs and, if needed, flips
    ctx.use_sequence_numbers to True. Returns the computed corruption ratio.

    - Uses ctx.imap.uid('FETCH', uid, '(RFC822)') to probe
    - Respects ctx.verbose for detailed prints
    - Prints critical warnings regardless of verbosity (treated as errors)
    """
    if not email_ids:
        return 0.0

    if getattr(ctx, 'verbose', False):
        print(f"🔍 Sprawdzam {min(10, len(email_ids))} UIDs które będą używane...")

    test_ids = email_ids[:10]
    corruption_count = 0

    for test_id in test_ids:
        try:
            result, test_data = ctx.imap.uid('FETCH', test_id, '(RFC822)')
            if getattr(ctx, 'verbose', False):
                print(f"🔍 Corruption test: UID {test_id} -> result='{result}', data={test_data}, type={type(test_data)}")

            is_corrupted = False
            if result != 'OK':
                is_corrupted = True
                if getattr(ctx, 'verbose', False):
                    print(f"   ❌ result != OK: {result}")
                else:
                    print(f"❌ Corruption UID {test_id}: result={result}")
            elif not test_data:
                is_corrupted = True
                if getattr(ctx, 'verbose', False):
                    print(f"   ❌ not test_data: {test_data}")
                else:
                    print(f"❌ Corruption UID {test_id}: empty data")
            elif test_data == [None]:
                is_corrupted = True
                if getattr(ctx, 'verbose', False):
                    print(f"   ❌ test_data == [None]: {test_data}")
                else:
                    print(f"❌ Corruption UID {test_id}: data=[None]")
            elif test_data and len(test_data) > 0 and test_data[0] is None:
                is_corrupted = True
                if getattr(ctx, 'verbose', False):
                    print(f"   ❌ test_data[0] is None: {test_data[0]}")
                else:
                    print(f"❌ Corruption UID {test_id}: first element None")
            else:
                if getattr(ctx, 'verbose', False):
                    print("   ✅ UID seems OK")

            if is_corrupted:
                corruption_count += 1

        except Exception as e:
            corruption_count += 1
            if getattr(ctx, 'verbose', False):
                print(f"🔍 Corruption test: UID {test_id} -> Exception: {e}")
            else:
                # Use ctx._short if available
                if hasattr(ctx, '_short'):
                    print(f"❌ Corruption UID {test_id}: Exception {ctx._short(e)}")
                else:
                    print(f"❌ Corruption UID {test_id}: Exception {e}")

    ratio = corruption_count / len(test_ids) if test_ids else 0.0
    if getattr(ctx, 'verbose', False):
        print(f"🔍 Corruption ratio: {ratio:.1%} ({corruption_count}/{len(test_ids)} UIDs)")

    if ratio > 0.8:
        print("🚨 WYKRYTO POWAŻNĄ CORRUPTION SKRZYNKI IMAP!")
        print("")
        print("Wszystkie UIDs w skrzynce są uszkodzone. To oznacza że:")
        print("- SEARCH zwraca UIDs które nie istnieją fizycznie")
        print("- FETCH nie może pobrać danych z tych UIDs")
        print("")
        print("🔄 AUTOMATYCZNE PRZEŁĄCZENIE NA TRYB AWARYJNY...")
        print("   Używam numerów sekwencyjnych zamiast UIDs")
        print("")
        ctx.use_sequence_numbers = True
    elif ratio > 0.2:
        print(f"⚠️  Wykryto częściową corruption ({ratio:.1%} UIDs uszkodzonych)")
        print("   Przełączam na tryb sekwencyjny...")
        ctx.use_sequence_numbers = True

    return ratio
