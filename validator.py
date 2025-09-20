# validator.py
import re

def validate_processed_data(data):
    """
    Pārbauda apstrādāto datu struktūras loģisko pareizību.
    - Pārbauda, vai panti ir secīgi.
    """
    messages = []
    if not data:
        messages.append("Validācijas kļūda: Datu saraksts ir tukšs.")
        return False, messages

    # Pārbaudām, vai ir iegūts likuma nosaukums
    if not all(item.get("law_title") and item["law_title"] != "Nezinams_likums" for item in data):
        messages.append("Brīdinājums: Vismaz vienam ierakstam trūkst likuma nosaukuma vai tas ir 'Nezinams_likums'.")

    # Loģiskās secības pārbaude
    last_article_num = 0
    for i, item in enumerate(data):
        if item.get("article"):
            # Iegūstam panta numuru no teksta, piem., "11.pants." -> 11
            match = re.match(r'(\d+)', item["article"])
            if match:
                article_num = int(match.group(1))
                if article_num < last_article_num:
                    messages.append(f"Validācijas kļūda: Pantu secība nav pareiza pie ieraksta Nr.{i+1}. Pants {article_num} seko pēc {last_article_num}.")
                last_article_num = article_num

    if messages:
        return False, messages

    return True, ["Dati ir strukturāli derīgi."]

