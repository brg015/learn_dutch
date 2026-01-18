"""
Test phrase detection logic.
"""

from scripts.import_basic_to_mongo import detect_entry_type
from core.schemas import EntryType

test_cases = [
    # (input, expected_type, description)
    ("huis", EntryType.WORD, "Single word"),
    ("de huis", EntryType.WORD, "Noun with 'de' article"),
    ("het huis", EntryType.WORD, "Noun with 'het' article"),
    ("houden tussen ons", EntryType.PHRASE, "Multi-word phrase"),
    ("op de hoogte", EntryType.PHRASE, "Phrase with 'de' in middle"),
    ("De Hague", EntryType.WORD, "Proper noun with article"),
    ("aan het werk", EntryType.PHRASE, "Phrase with 'het' in middle"),
    ("lopen", EntryType.WORD, "Single verb"),
]

print("Testing phrase detection:")
print("=" * 60)

all_passed = True
for dutch, expected, description in test_cases:
    result = detect_entry_type(dutch)
    passed = result == expected
    status = "✓" if passed else "✗"

    print(f"{status} '{dutch}' → {result.value}")
    print(f"  Expected: {expected.value} ({description})")

    if not passed:
        all_passed = False
    print()

print("=" * 60)
if all_passed:
    print("All tests passed!")
else:
    print("Some tests failed!")
