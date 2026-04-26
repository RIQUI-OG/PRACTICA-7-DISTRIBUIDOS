from fastapi import FastAPI
from modelo import NoteIn, NoteOut, Notes
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Permite todos los orígenes
    allow_credentials=True,    # Permite cookies y credenciales
    allow_methods=["*"],         # Permite todos los métodos HTTP (GET, POST, etc.)
    allow_headers=["*"],         # Permite todas las cabeceras
)

notes_db = Notes()

@app.post("/{user}", status_code=201)
def add_note(user: str, note: NoteIn):
    notes_db.add_note(user, note)
    return {"message": "Note added successfully"}

@app.get("/{user}", response_model=list[NoteOut], status_code=200)
def get_notes(user: str):
    return notes_db.get_notes(user)

@app.get("/{user}/{id}", response_model=NoteOut, status_code=200)
def get_note(user: str, id: int):
    note = notes_db.get_note(user, id)
    if note is not None:
        return note
    return NoteOut(id=-1, title="Not Found", note="")

@app.put("/{user}/{id}", status_code=200)
def modify_note(user: str, id: int, note: NoteIn):
    if notes_db.modify_note(user, id, note.title, note.note):
        return {"message": "Note modified successfully"}
    return {"error": "Note not found"}

@app.delete("/{user}/{id}", status_code=204)
def delete_note(user: str, id: int):
    if notes_db.delete_note(user, id):
        return {"message": "Note deleted successfully"}
    return {"error": "Note not found"}

