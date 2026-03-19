NOTES_FILE = "notes.txt"
SEPARATOR = "\n---\n"
MAX_NOTES = 50


def _load_raw():
    try:
        with open(NOTES_FILE, "r") as f:
            return f.read()
    except OSError:
        return ""


def _save_raw(data):
    with open(NOTES_FILE, "w") as f:
        f.write(data)


def load_notes():
    raw = _load_raw()
    if not raw.strip():
        return []
    return [n for n in raw.split(SEPARATOR) if n.strip()]


def save_notes(notes):
    _save_raw(SEPARATOR.join(notes))


def add_note(text):
    text = text.strip()
    if not text:
        return
    notes = load_notes()
    notes.insert(0, text)
    if len(notes) > MAX_NOTES:
        notes = notes[:MAX_NOTES]
    save_notes(notes)


def delete_note(index):
    notes = load_notes()
    if 0 <= index < len(notes):
        notes.pop(index)
        save_notes(notes)


def edit_note(index, text):
    text = text.strip()
    if not text:
        return
    notes = load_notes()
    if 0 <= index < len(notes):
        notes[index] = text
        save_notes(notes)
