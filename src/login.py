# login.py
import os
import sys
import json
import base64
import hashlib
import secrets
from pathlib import Path
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.app import App
from kivy.core.window import Window

# local storage path para credenciais (persistente)
def get_user_store_path():
    """
    Retorna o caminho completo para o ficheiro users.json onde guardamos
    as credenciais (salt + hash). Diretório padrão:
      Windows: %APPDATA%/RegistroAtividades/users.json
      Linux/Mac: ~/.local/share/RegistroAtividades/users.json
    """
    if sys.platform.startswith("win"):
        base = os.getenv("APPDATA") or Path.home()
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    folder = Path(base) / "RegistroAtividades"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "users.json"

# Hashing seguro: PBKDF2-HMAC-SHA256
def hash_password(password: str, salt: bytes = None, iterations: int = 200_000):
    if salt is None:
        salt = secrets.token_bytes(16)
    pwd = password.encode('utf-8')
    dk = hashlib.pbkdf2_hmac('sha256', pwd, salt, iterations)
    return {
        "salt": base64.b64encode(salt).decode('ascii'),
        "hash": base64.b64encode(dk).decode('ascii'),
        "iters": iterations
    }

def verify_password(password: str, salt_b64: str, hash_b64: str, iterations: int):
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return secrets.compare_digest(dk, expected)

def load_users():
    path = get_user_store_path()
    if not path.exists():
        return {}  # vazio
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(users: dict):
    path = get_user_store_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# LoginScreen com botão de criação de conta
class LoginScreen(Screen):
    def fazer_login(self, username, password):
        username = (username or "").strip()
        password = (password or "").strip()
        if not username or not password:
            self.show_error("Por favor, preencha todos os campos.")
            return

        users = load_users()
        record = users.get(username)
        if not record:
            self.show_error("Usuário não encontrado. Cadastre-se primeiro.")
            return

        try:
            ok = verify_password(password, record["salt"], record["hash"], int(record.get("iters", 200000)))
        except Exception:
            ok = False

        if ok:
            # login OK
            app = App.get_running_app()
            app.user_id = username
            app.sm.current = 'main'
            try:
                main_screen = app.sm.get_screen('main')
                main_screen.carregar_atividades()
            except Exception:
                pass
        else:
            self.show_error("Usuário ou senha incorretos.")
            try:
                self.ids.password.text = ""
            except Exception:
                pass

    def criar_conta_popup(self):
        """
        Abre popup para criar conta. O popup tem 3 campos: usuário, senha e confirmar senha.
        """
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        layout = BoxLayout(orientation='vertical', padding=8, spacing=8)
        layout.add_widget(Label(text="Novo usuário:"))
        username_input = TextInput(multiline=False)
        layout.add_widget(username_input)
        layout.add_widget(Label(text="Senha:"))
        password_input = TextInput(password=True, multiline=False)
        layout.add_widget(password_input)
        layout.add_widget(Label(text="Confirmar senha:"))
        confirm_input = TextInput(password=True, multiline=False)
        layout.add_widget(confirm_input)

        buttons = BoxLayout(size_hint_y=None, height=40, spacing=8)
        ok_btn = Button(text="Criar")
        cancel_btn = Button(text="Cancelar")
        buttons.add_widget(ok_btn)
        buttons.add_widget(cancel_btn)
        layout.add_widget(buttons)

        popup = Popup(title="Criar Conta", content=layout, size_hint=(0.9, 0.6))

        def on_cancel(inst):
            popup.dismiss()

        def on_create(inst):
            user = (username_input.text or "").strip()
            pwd = (password_input.text or "").strip()
            conf = (confirm_input.text or "").strip()
            if not user or not pwd:
                self.show_error("Preencha usuário e senha.")
                return
            if pwd != conf:
                self.show_error("Senha e confirmação não coincidem.")
                return
            users = load_users()
            if user in users:
                self.show_error("Usuário já existe. Escolha outro nome.")
                return
            # criar hash
            rec = hash_password(pwd)
            users[user] = rec
            try:
                save_users(users)
            except Exception as e:
                self.show_error(f"Falha ao salvar usuário: {e}")
                return
            popup.dismiss()
            self._show_info("Conta criada com sucesso. Faça login.")

        ok_btn.bind(on_release=on_create)
        cancel_btn.bind(on_release=on_cancel)
        popup.open()

    def _show_info(self, message):
        popup = Popup(title='Info', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def show_error(self, message):
        popup = Popup(title='Erro', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    # Tab/Enter handling (já implementado anteriormente)
    def on_pre_enter(self, *args):
        Window.bind(on_key_down=self._on_key_down)

    def on_leave(self, *args):
        try:
            Window.unbind(on_key_down=self._on_key_down)
        except Exception:
            pass

    def _on_key_down(self, window, key, scancode, codepoint, modifiers):
        # Tab (9) e Enter (13)
        try:
            if key == 9 or codepoint == '\t':
                try:
                    if self.ids.username.focus:
                        self.ids.username.focus = False
                        self.ids.password.focus = True
                    elif self.ids.password.focus:
                        self.ids.password.focus = False
                        self.ids.username.focus = True
                    else:
                        self.ids.username.focus = True
                except Exception:
                    pass
                return True
            if key == 13 or codepoint in ('\r', '\n'):
                try:
                    u = self.ids.username.text.strip()
                    p = self.ids.password.text.strip()
                    if u and p:
                        self.fazer_login(u, p)
                except Exception:
                    pass
                return True
        except Exception:
            pass
        return False
