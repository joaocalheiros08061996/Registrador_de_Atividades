import sys
import os
from kivy.resources import resource_add_path
from dotenv import load_dotenv

def adicionar_caminhos_kv() -> None:
    # Se executável onefile extrair arquivos, adiciona o caminho de recursos para Kivy
    if getattr(sys, '_MEIPASS', None):
        resource_add_path(os.path.join(sys._MEIPASS))

def carregar_env() -> None:
    """
    Prioridade:
      1) .env externo (arquivo ao lado do exe)
      2) .env embutido extraído em sys._MEIPASS (quando onefile)
      3) variáveis do sistema (os.environ)
    """
    # 1) pasta do executável (quando empacotado) ou cwd em dev
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.abspath(os.getcwd())

    external_env = os.path.join(exe_dir, ".env")
    if os.path.exists(external_env):
        load_dotenv(external_env)
        return

    # 2) .env embutido extraído em _MEIPASS (onefile)
    base = getattr(sys, "_MEIPASS", None)
    if base:
        bundled_env = os.path.join(base, ".env")
        if os.path.exists(bundled_env):
            load_dotenv(bundled_env)
            return

    # 3) se nada encontrado, não faz nada (usa variáveis do sistema, se existirem)
    return

# Agora importa o Kivy / telas
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivy.properties import StringProperty

# Importar telas só após carregar env
from src.login import LoginScreen
from src.GUI import MainScreen


def carregar_arquivos_kv() -> None: 
    # Carregar os arquivos KV (devem estar na mesma pasta do exe / ou embutidos)
    Builder.load_file('kv/login.kv')
    Builder.load_file('kv/main.kv')

class ActivityTrackerApp(MDApp):
    user_id = StringProperty("")

    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(MainScreen(name='main'))
        return self.sm