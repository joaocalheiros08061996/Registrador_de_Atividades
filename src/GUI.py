# GUI.py (substituir)
from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.button import Button
from kivymd.app import MDApp
import src.handle_db as db

# Cores (RGBA 0-1): ajuste como preferir
NORMAL_COLOR = (1, 1, 1, 1)            # cor normal do botão
SELECTED_COLOR = (0.2, 0.6, 0.2, 1)    # cor quando selecionado (verde)
DISABLED_COLOR = (0.7, 0.7, 0.7, 1)    # cor quando desabilitado (opcional)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_activity_id = None
        self.selected_activity_type = None
        self.selected_button = None  # referência ao ToggleButton selecionado

    def carregar_atividades(self):
        self.app = MDApp.get_running_app()

        activity_types = [
            "Pesquisa e Desenvolvimento",
            "Atendimento na Fábrica",
            "Documentação",
            "Confecção de Gabaritos",
            "Cadastro",
            "Reuniões"
        ]

        activity_buttons = self.ids.activity_buttons
        activity_buttons.clear_widgets()

        # Criar ToggleButtons em grupo 'activity' (apenas 1 fica 'down' ao mesmo tempo)
        for activity_type in activity_types:
            btn = ToggleButton(
                text=activity_type,
                size_hint_y=None,
                height=48,
                group='activity',
                background_color=NORMAL_COLOR,
                allow_no_selection=False
            )
            # quando o estado muda, atualiza a seleção
            btn.bind(state=lambda inst, st, at=activity_type: self.on_activity_toggled(inst, st, at))
            activity_buttons.add_widget(btn)

        # Verifica se existe atividade em andamento para o usuário atual
        self.verificar_atividade_em_andamento()

    def on_activity_toggled(self, inst, state, activity_type):
        """
        inst: ToggleButton
        state: 'down' ou 'normal'
        activity_type: nome do tipo
        """
        if state == 'down':
            # marcar seleção
            self.selected_button = inst
            self.selected_activity_type = activity_type
            # muda cor pra selecionado
            try:
                inst.background_color = SELECTED_COLOR
            except Exception:
                pass
            # atualizar label (pré-início)
            try:
                self.ids.selected_activity_label.text = f"Selecionado: {activity_type}"
            except Exception:
                pass
        else:
            # voltar cor ao normal
            try:
                inst.background_color = NORMAL_COLOR
            except Exception:
                pass
            # se o botão liberado era o selecionado, limpa seleção
            if self.selected_button is inst:
                self.selected_button = None
                self.selected_activity_type = None
                try:
                    self.ids.selected_activity_label.text = "Nenhuma atividade selecionada"
                except Exception:
                    pass

    def acao_iniciar(self):
        if not self.selected_activity_type:
            self.show_error("Por favor, selecione um tipo de atividade.")
            return

        descricao = ""
        try:
            descricao = self.ids.descricao_text.text
        except Exception:
            pass

        try:
            # iniciar atividade no DB
            self.current_activity_id = db.iniciar_nova_atividade(
                self.selected_activity_type, descricao, MDApp.get_running_app().user_id
            )
            # Atualizar estado UI
            try:
                self.ids.status_label.text = f"Em andamento: {self.selected_activity_type}"
            except Exception:
                pass
            # mostra a caixa com o título da atividade e mantém a cor do botão selecionado
            self._show_active_box(self.selected_activity_type)
            self._set_state_em_andamento(True)
        except Exception as e:
            self.show_error(f"Falha ao iniciar atividade:\n{e}")

    def acao_finalizar(self):
        if not self.current_activity_id:
            self.show_error("Não há atividade em andamento para finalizar.")
            return

        try:
            db.finalizar_atividade(self.current_activity_id)
            self.show_success("Atividade finalizada com sucesso.")
            self.current_activity_id = None

            # limpar seleção visual: botão volta ao normal
            if self.selected_button:
                try:
                    self.selected_button.state = 'normal'   # dispara on_activity_toggled -> cor normal
                    self.selected_button = None
                except Exception:
                    pass

            self.selected_activity_type = None
            try:
                self.ids.selected_activity_label.text = "Nenhuma atividade selecionada"
                self.ids.descricao_text.text = ""
                self.ids.status_label.text = "Pronto para começar."
            except Exception:
                pass

            # esconder a caixa de atividade ativa
            self._show_active_box(None)
            self._set_state_em_andamento(False)
        except Exception as e:
            self.show_error(f"Falha ao finalizar atividade:\n{e}")

    def verificar_atividade_em_andamento(self):
        try:
            user_id = MDApp.get_running_app().user_id
            row = db.buscar_atividade_em_andamento(user_id)
            if row:
                # existe atividade em andamento -> ajustar UI
                self.current_activity_id = row.get("id")
                tipo = row.get("tipo_atividade")
                self.selected_activity_type = tipo
                # tenta marcar o ToggleButton correspondente como 'down'
                for btn in list(self.ids.activity_buttons.children):
                    if getattr(btn, 'text', None) == tipo:
                        btn.state = 'down'      # acionará on_activity_toggled e mudará cor
                        self.selected_button = btn
                    else:
                        # opcional: deixar os outros habilitados mas não selecionados
                        pass

                self.ids.selected_activity_label.text = f"Continuando: {tipo}"
                self.ids.descricao_text.text = row.get("descricao") or ""
                self.ids.status_label.text = f"Continuando: {tipo}"
                # mostrar box ativa
                self._show_active_box(tipo)
                self._set_state_em_andamento(True)
            else:
                self._set_state_em_andamento(False)
        except Exception as e:
            print("Aviso: falha ao verificar atividade em andamento:", e)
            self._set_state_em_andamento(False)

    def _set_state_em_andamento(self, em_andamento):
        try:
            self.ids.start_button.disabled = em_andamento
            self.ids.end_button.disabled = not em_andamento
            self.ids.descricao_text.disabled = em_andamento
        except Exception:
            pass

        # opcional: desabilitar todos os botões enquanto em andamento (se quiser)
        for btn in list(self.ids.activity_buttons.children):
            try:
                # se você preferir que o usuário não mude a seleção enquanto em andamento:
                btn.disabled = em_andamento and (btn is not self.selected_button)
            except Exception:
                pass

    def _show_active_box(self, tipo_atividade_or_none):
        """
        Controla a visibilidade e texto da caixa que mostra a atividade em andamento.
        Se tipo_atividade_or_none for None, esconde a caixa; caso contrário mostra com o texto.
        """
        try:
            if tipo_atividade_or_none:
                self.ids.active_box.height = 48
                self.ids.active_box.opacity = 1
                self.ids.active_label.text = f"Atividade em andamento: {tipo_atividade_or_none}"
            else:
                self.ids.active_box.height = 0
                self.ids.active_box.opacity = 0
                self.ids.active_label.text = ""
        except Exception:
            pass

    def show_error(self, message):
        popup = Popup(title='Erro', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def show_success(self, message):
        popup = Popup(title='Sucesso', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def logout(self):
        app = MDApp.get_running_app()
        app.user_id = ""
        app.sm.current = 'login'
