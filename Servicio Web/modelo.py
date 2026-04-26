from pydantic import BaseModel

class NoteIn(BaseModel):
    title: str
    note: str

class NoteOut(BaseModel):
    id: int
    title: str
    note: str

class Notes:
    def __init__(self):
        self.notes = {}
        self.last_id = {}

    def add_note(self, user: str, nota: NoteIn):
        if user not in self.notes:
            self.notes[user] = []
            self.last_id[user] = 0
        self.notes[user].insert(0, NoteOut(id=self.last_id[user], title=nota.title, note=nota.note))
        self.last_id[user] += 1

    def get_notes(self, user: str):
        return list(map(lambda x: NoteOut(id=x.id, title=x.title, note=(x.note[:10] + '...' if len(x.note) > 10 else x.note)), self.notes.get(user, [])))

    def get_note(self, user: str, id: int):
        if user in self.notes:
            for note in self.notes[user]:
                if note.id == id:
                    return note
        return None
    
    def modify_note(self, user: str, id: int, new_title: str, new_note: str):
        if user in self.notes:
            for note in self.notes[user]:
                if note.id == id:
                    note.title = new_title
                    note.note = new_note
                    return True
        return False
    
    def delete_note(self, user: str, id: int):
        if user in self.notes:
            for i, note in enumerate(self.notes[user]):
                if note.id == id:
                    del self.notes[user][i]
                    return True
        return False