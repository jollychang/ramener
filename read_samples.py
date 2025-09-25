from pathlib import Path
from ramener.pdf_extractor import extract_text
from ramener.text_sanitizer import sanitize_excerpt

path = Path("/Users/william/Downloads/Confirmation_for_Booking_ID_#_896218506.pdf")
text = extract_text(path, page_limit=3, max_chars=2000)
print(text[:500])
print("---")
print(sanitize_excerpt(text)[:500])
