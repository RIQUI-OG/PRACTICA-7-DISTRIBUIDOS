# Pérez Hernández Ricardo — Práctica 5: Servicios Web
# ─────────────────────────────────────────────────────────────────────────────
# chat_cliente.py  —  Cliente de Chat que consume la API REST (Chat y Notas)
# ─────────────────────────────────────────────────────────────────────────────
import requests
import threading
import time
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import queue

# ── Configuración de Endpoints ────────────────────────────────────────────────
HOST = 'localhost'
PORT_CHAT = 9000
PORT_NOTAS = 8000

URL_CHAT  = f"http://{HOST}:{PORT_CHAT}"
URL_NOTAS = f"http://{HOST}:{PORT_NOTAS}"

POLL_INTERVAL      = 1.0   
HEARTBEAT_INTERVAL = 5.0   

# ─────────────────────────────────────────────────────────────────────────────
# CLASE CLIENTE DE CHAT (Flask - Puerto 9000)
# ─────────────────────────────────────────────────────────────────────────────
class ChatCliente:
    def __init__(self, usuario: str):
        self.usuario    = usuario
        self.ultimo_id  = 0      
        self._activo    = False

    def unirse(self) -> bool:
        try:
            r = requests.post(f"{URL_CHAT}/unirse", json={'usuario': self.usuario}, timeout=5)
            return r.ok
        except Exception:
            return False

    def salir(self):
        try:
            requests.delete(f"{URL_CHAT}/salir", json={'usuario': self.usuario}, timeout=3)
        except Exception:
            pass

    def enviar(self, texto: str) -> bool:
        try:
            r = requests.post(f"{URL_CHAT}/mensajes", json={'usuario': self.usuario, 'texto': texto}, timeout=5)
            return r.ok
        except Exception:
            return False

    def obtener_nuevos(self) -> list:
        try:
            r = requests.get(f"{URL_CHAT}/mensajes", params={'desde': self.ultimo_id}, timeout=5)
            if not r.ok: return []
            nuevos = r.json().get('mensajes', [])
            if nuevos: self.ultimo_id = nuevos[-1]['id']
            return nuevos
        except Exception:
            return []

    def obtener_usuarios(self) -> list:
        try:
            r = requests.get(f"{URL_CHAT}/usuarios", timeout=5)
            return r.json().get('usuarios', []) if r.ok else []
        except Exception:
            return []

    def heartbeat(self):
        try:
            requests.post(f"{URL_CHAT}/heartbeat", json={'usuario': self.usuario}, timeout=3)
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# CLASE CLIENTE DE NOTAS (FastAPI - Puerto 8000)
# ─────────────────────────────────────────────────────────────────────────────
class NotasCliente:
    """
    Encapsula las llamadas HTTP al microservicio de Notas (FastAPI).
    Implementa el CRUD sobre el modelo NoteIn / NoteOut.
    """
    def __init__(self, usuario: str):
        self.usuario = usuario

    def agregar(self, titulo: str, nota: str) -> bool:
        try:
            r = requests.post(f"{URL_NOTAS}/{self.usuario}", json={"title": titulo, "note": nota}, timeout=5)
            return r.status_code == 201
        except Exception as e:
            print(f"[ERROR NOTAS] agregar: {e}")
            return False

    def listar(self) -> list:
        try:
            r = requests.get(f"{URL_NOTAS}/{self.usuario}", timeout=5)
            return r.json() if r.status_code == 200 else []
        except Exception:
            return []

    def eliminar(self, id_nota: int) -> bool:
        try:
            r = requests.delete(f"{URL_NOTAS}/{self.usuario}/{id_nota}", timeout=5)
            return r.status_code == 204
        except Exception:
            return False

# ─────────────────────────────────────────────────────────────────────────────
# GUI TKINTER
# ─────────────────────────────────────────────────────────────────────────────
class ChatGUI:
    def __init__(self, root: tk.Tk, cliente_chat: ChatCliente, cliente_notas: NotasCliente):
        self.root = root
        self.cliente = cliente_chat
        self.notas = cliente_notas
        self.cola = queue.Queue()

        self._construir_ui()
        self._iniciar_hilos()
        self.root.after(200, self._procesar_cola)

    def _construir_ui(self):
        self.root.title(f"Chat REST & Notas API — {self.cliente.usuario}")
        self.root.configure(bg='#1a1a2e')
        self.root.resizable(False, False)

        barra = tk.Frame(self.root, bg='#16213e', pady=6)
        barra.pack(fill='x')

        tk.Label(barra, text="💬 CHAT & NOTAS (REST API)", font=("Consolas", 11, "bold"), bg='#16213e', fg='#00d4ff').pack(side='left', padx=12)
        self.lbl_usuario = tk.Label(barra, text=f"● {self.cliente.usuario}", font=("Consolas", 9), bg='#16213e', fg='#00ff88')
        self.lbl_usuario.pack(side='right', padx=12)

        contenido = tk.Frame(self.root, bg='#1a1a2e')
        contenido.pack(fill='both', expand=True, padx=8, pady=(6, 0))

        frame_msgs = tk.Frame(contenido, bg='#1a1a2e')
        frame_msgs.pack(side='left', fill='both', expand=True)

        tk.Label(frame_msgs, text="MENSAJES (Usa /nota para comandos de FastAPI)", font=("Consolas", 8), bg='#1a1a2e', fg='#555577').pack(anchor='w')

        self.txt_mensajes = scrolledtext.ScrolledText(
            frame_msgs, width=62, height=22, font=("Consolas", 9),
            bg='#0d1117', fg='#c9d1d9', insertbackground='white',
            relief='flat', bd=0, state='disabled'
        )
        self.txt_mensajes.pack(fill='both', expand=True)
        self.txt_mensajes.tag_config('sistema', foreground='#555577')
        self.txt_mensajes.tag_config('notas', foreground='#d2a8ff') # Color para la API de Notas
        self.txt_mensajes.tag_config('propio', foreground='#79c0ff')
        self.txt_mensajes.tag_config('otro', foreground='#56d364')
        self.txt_mensajes.tag_config('hora', foreground='#444466')

        frame_lat = tk.Frame(contenido, bg='#16213e', width=160, padx=8)
        frame_lat.pack(side='right', fill='y', padx=(8, 0))
        frame_lat.pack_propagate(False)

        tk.Label(frame_lat, text="CONECTADOS", font=("Consolas", 8, "bold"), bg='#16213e', fg='#00d4ff').pack(anchor='w', pady=(6, 2))
        self.lst_usuarios = tk.Listbox(frame_lat, font=("Consolas", 9), bg='#0d1117', fg='#00ff88', selectbackground='#21262d', relief='flat', bd=0, activestyle='none')
        self.lst_usuarios.pack(fill='both', expand=True)

        tk.Label(self.root, text="PETICIONES HTTP", font=("Consolas", 7), bg='#1a1a2e', fg='#555577').pack(anchor='w', padx=8)
        self.txt_http = tk.Text(self.root, height=4, width=80, font=("Consolas", 7), bg='#0d1117', fg='#6e7681', relief='flat', bd=0, state='disabled')
        self.txt_http.pack(fill='x', padx=8, pady=(0, 4))

        frame_entrada = tk.Frame(self.root, bg='#21262d', pady=6)
        frame_entrada.pack(fill='x', padx=8, pady=(0, 8))

        self.entrada = tk.Entry(frame_entrada, font=("Consolas", 10), bg='#21262d', fg='white', insertbackground='white', relief='flat', bd=4)
        self.entrada.pack(side='left', fill='x', expand=True, ipady=4)
        self.entrada.bind('<Return>', self._procesar_entrada)
        self.entrada.focus()

        btn = tk.Button(frame_entrada, text="Enviar", font=("Consolas", 9, "bold"), bg='#238636', fg='white', activebackground='#2ea043', relief='flat', bd=0, padx=14, pady=4, command=self._procesar_entrada)
        btn.pack(side='right', padx=(6, 0))

    def _iniciar_hilos(self):
        threading.Thread(target=self._hilo_polling, daemon=True).start()
        threading.Thread(target=self._hilo_heartbeat, daemon=True).start()

    def _hilo_polling(self):
        while True:
            nuevos = self.cliente.obtener_nuevos()
            for msg in nuevos:
                self.cola.put(('mensaje', msg))
            if nuevos:
                self._log_http(f"GET Chat /mensajes?desde={self.cliente.ultimo_id - len(nuevos)} → {len(nuevos)} nuevo(s)")

            if int(time.time()) % 3 == 0:
                usuarios = self.cliente.obtener_usuarios()
                self.cola.put(('usuarios', usuarios))

            time.sleep(POLL_INTERVAL)

    def _hilo_heartbeat(self):
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            self.cliente.heartbeat()

    def _procesar_cola(self):
        try:
            while not self.cola.empty():
                tipo, datos = self.cola.get_nowait()
                if tipo == 'mensaje': self._mostrar_mensaje(datos)
                elif tipo == 'usuarios': self._actualizar_usuarios(datos)
        except queue.Empty: pass
        self.root.after(200, self._procesar_cola)

    def _mostrar_mensaje(self, msg: dict):
        self.txt_mensajes.config(state='normal')
        hora = msg.get('timestamp', time.strftime('%H:%M:%S'))
        usr  = msg.get('usuario', '')
        txt  = msg.get('texto', '')

        if usr == 'SISTEMA':
            self.txt_mensajes.insert('end', f"  {txt}\n", 'sistema')
        elif usr == 'API_NOTAS':
            self.txt_mensajes.insert('end', f"[{hora}] 📝 [NOTAS]: {txt}\n", 'notas')
        elif usr == self.cliente.usuario:
            self.txt_mensajes.insert('end', f"[{hora}] ", 'hora')
            self.txt_mensajes.insert('end', f"Tú: {txt}\n", 'propio')
        else:
            self.txt_mensajes.insert('end', f"[{hora}] ", 'hora')
            self.txt_mensajes.insert('end', f"{usr}: {txt}\n", 'otro')

        self.txt_mensajes.config(state='disabled')
        self.txt_mensajes.see('end')

    def _actualizar_usuarios(self, usuarios: list):
        self.lst_usuarios.delete(0, 'end')
        for u in usuarios:
            prefijo = "► " if u == self.cliente.usuario else "  "
            self.lst_usuarios.insert('end', f"{prefijo}{u}")

    def _log_http(self, texto: str):
        self.txt_http.config(state='normal')
        self.txt_http.insert('end', f"{time.strftime('%H:%M:%S')} {texto}\n")
        if int(self.txt_http.index('end-1c').split('.')[0]) > 6:
            self.txt_http.delete('1.0', '2.0')
        self.txt_http.config(state='disabled')
        self.txt_http.see('end')

    def _imprimir_local(self, origen: str, texto: str):
        """Simula la llegada de un mensaje para renderizar respuestas locales sin enviarlas al servidor de chat."""
        self.cola.put(('mensaje', {'usuario': origen, 'texto': texto, 'timestamp': time.strftime('%H:%M:%S')}))

    # ── Orquestador de Entradas ───────────────────────────────────────────────
    def _procesar_entrada(self, event=None):
        texto = self.entrada.get().strip()
        if not texto: return
        self.entrada.delete(0, 'end')

        # Interceptar comandos del microservicio de Notas
        if texto.startswith('/nota'):
            self._manejar_api_notas(texto)
            return

        # Flujo normal hacia el servidor de Chat
        ok = self.cliente.enviar(texto)
        self._log_http(f"POST Chat /mensajes → {'200 OK' if ok else 'ERROR'}")

    def _manejar_api_notas(self, texto: str):
        """Parsea comandos para consumir la API de Notas en FastAPI."""
        partes = texto.split(' ', 2)
        comando = partes[1] if len(partes) > 1 else ''

        if comando == 'add' and len(partes) > 2:
            datos = partes[2].split('|', 1)
            titulo = datos[0].strip()
            contenido = datos[1].strip() if len(datos) > 1 else "Sin descripción"
            
            if self.notas.agregar(titulo, contenido):
                self._imprimir_local("API_NOTAS", f"Nota creada exitosamente: '{titulo}'")
                self._log_http(f"POST Notas /{self.cliente.usuario} → 201 Created")
            else:
                self._imprimir_local("API_NOTAS", "Error HTTP al crear la nota.")

        elif comando == 'list':
            notas = self.notas.listar()
            self._log_http(f"GET Notas /{self.cliente.usuario} → 200 OK")
            if not notas:
                self._imprimir_local("API_NOTAS", "El repositorio está vacío para este usuario.")
            else:
                self._imprimir_local("API_NOTAS", "--- Listado de Notas ---")
                for n in notas:
                    self._imprimir_local("API_NOTAS", f"ID: {n['id']} | {n['title']} -> {n['note']}")

        elif comando == 'del' and len(partes) > 2:
            try:
                id_nota = int(partes[2].strip())
                if self.notas.eliminar(id_nota):
                    self._imprimir_local("API_NOTAS", f"Nota {id_nota} purgada del sistema.")
                    self._log_http(f"DELETE Notas /{self.cliente.usuario}/{id_nota} → 204 No Content")
                else:
                    self._imprimir_local("API_NOTAS", f"Fallo al eliminar. ¿Existe el ID {id_nota}?")
            except ValueError:
                self._imprimir_local("API_NOTAS", "El ID de la nota debe ser un valor entero (Integer).")
        else:
            self._imprimir_local("API_NOTAS", "Sintaxis inválida. Uso: /nota [add Título | Contenido] o [/nota list] o [/nota del ID]")

def main():
    root_login = tk.Tk()
    root_login.withdraw()
    usuario = simpledialog.askstring("Chat REST", "Ingresa tu nombre de usuario:", parent=root_login)
    root_login.destroy()

    if not usuario or not usuario.strip(): return
    usuario = usuario.strip()

    cliente_chat = ChatCliente(usuario)
    cliente_notas = NotasCliente(usuario)

    if not cliente_chat.unirse():
        messagebox.showerror("Error", f"No se pudo contactar al servidor Flask en {URL_CHAT}")
        return

    root = tk.Tk()
    app  = ChatGUI(root, cliente_chat, cliente_notas)
    root.protocol("WM_DELETE_WINDOW", lambda: (cliente_chat.salir(), root.destroy()))
    root.mainloop()

if __name__ == '__main__':
    main()