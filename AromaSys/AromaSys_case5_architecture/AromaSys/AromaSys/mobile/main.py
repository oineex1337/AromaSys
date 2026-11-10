import re
import threading
from copy import deepcopy

import requests

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import AsyncImage
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget


# Адрес локального Flask API. Все операции приложения выполняются через HTTP API.
API_URL = "http://152.228.114.127"

try:
    from admin_config import ADMIN_EMAIL
except ImportError:
    ADMIN_EMAIL = ""

ACCENT_HEX = "#eeb921"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

GENDERS = ("Мужские", "Женские", "Унисекс")
CONCENTRATIONS = ("Parfum", "Extrait de Parfum", "Eau de Parfum", "Eau de Toilette", "Eau de Cologne")

CHIPS = ["Женские", "Мужские", "Унисекс"]
TILES = [
    ("Каталог", "Коллекция парфюмерии"),
    ("Избранное", "Сохранённые ароматы"),
    ("Мои заказы", "История и статусы"),
    ("Профиль", "Данные аккаунта"),
]


def paint(app, widget, key, radius=0):
    """Отрисовывает фон виджета с учётом текущей темы."""
    def draw(*_):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*app.colors[key])
            if radius:
                RoundedRectangle(pos=widget.pos, size=widget.size, radius=[dp(radius)])
            else:
                Rectangle(pos=widget.pos, size=widget.size)

    widget.bind(pos=draw, size=draw)
    draw()


class Card(BoxLayout):
    def __init__(self, app, key="panel", radius=8, **kwargs):
        super().__init__(**kwargs)
        paint(app, self, key, radius)


class ModernInput(TextInput):
    def __init__(self, app, **kwargs):
        c = app.colors
        super().__init__(
            background_normal="",
            background_active="",
            background_color=c["input"],
            foreground_color=c["text"],
            hint_text_color=c["muted"],
            cursor_color=c["text"],
            selection_color=c["selection"],
            padding=[dp(16), dp(15)],
            font_size=dp(15),
            multiline=False,
            size_hint_y=None,
            height=dp(52),
            **kwargs,
        )


class AromaButton(Button):
    VARIANTS = {
        "primary": ("primary", "primary_text"),
        "soft": ("soft", "text"),
        "panel": ("panel", "text"),
        "ghost": ("bg", "muted"),
        "danger": ("danger", "primary_text"),
    }

    def __init__(self, app, variant="primary", **kwargs):
        bg_key, fg_key = self.VARIANTS[variant]
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(52))
        super().__init__(
            background_normal="",
            background_down="",
            background_color=(0, 0, 0, 0),
            color=app.colors[fg_key],
            font_size=dp(14),
            bold=True,
            **kwargs,
        )
        paint(app, self, bg_key, radius=6)


class AromaSysApp(App):
    title = "AromaSys"

    THEMES = {
        "light": {
            "bg": (1, 1, 1, 1),
            "panel": (0.965, 0.965, 0.965, 1),
            "input": (0.945, 0.945, 0.945, 1),
            "text": (0.07, 0.07, 0.07, 1),
            "muted": (0.45, 0.45, 0.45, 1),
            "accent": (0.93, 0.73, 0.13, 1),
            "accent_text": (0.62, 0.45, 0.02, 1),
            "primary": (0.07, 0.07, 0.07, 1),
            "primary_text": (1, 1, 1, 1),
            "soft": (0.935, 0.935, 0.935, 1),
            "promo": (0.93, 0.73, 0.13, 1),
            "promo_text": (0.07, 0.07, 0.07, 1),
            "selection": (0.93, 0.73, 0.13, 0.35),
            "divider": (0.88, 0.88, 0.88, 1),
            "danger": (0.80, 0.15, 0.15, 1),
        },
        "dark": {
            "bg": (0.07, 0.07, 0.07, 1),
            "panel": (0.13, 0.13, 0.13, 1),
            "input": (0.17, 0.17, 0.17, 1),
            "text": (0.97, 0.97, 0.97, 1),
            "muted": (0.62, 0.62, 0.62, 1),
            "accent": (0.93, 0.73, 0.13, 1),
            "accent_text": (0.93, 0.73, 0.13, 1),
            "primary": (0.97, 0.97, 0.97, 1),
            "primary_text": (0.07, 0.07, 0.07, 1),
            "soft": (0.18, 0.18, 0.18, 1),
            "promo": (0.93, 0.73, 0.13, 1),
            "promo_text": (0.07, 0.07, 0.07, 1),
            "selection": (0.93, 0.73, 0.13, 0.35),
            "divider": (0.22, 0.22, 0.22, 1),
            "danger": (0.75, 0.20, 0.18, 1),
        },
    }

    def build(self):
        self.theme_name = "light"
        self.colors = self.THEMES[self.theme_name]
        self.current_username = ""
        self.current_email = ""
        self.current_user_id = None
        self.auth_token = None
        self.delivery_address = ""
        self.delivery_address_draft = ""
        self.active_screen = "login"
        self.catalog_gender = None
        self.catalog_query = ""
        self.catalog_sort = "title"
        self.catalog_order = "asc"
        self.catalog_cache = []
        self.local_products = []
        self.next_local_product_id = -1
        self.product_overrides = {}
        self.deleted_product_ids = set()
        self.local_favorites = set()
        self.selected_product = None
        self.detail_return_screen = "catalog"
        self.detail_return_scroll_y = 1.0
        self.current_scroll = None
        self.product_form_item = None
        self.profile_values = {}
        self.auth_values = {"login_email": "", "login_password": "", "reg_name": "", "reg_email": ""}

        self.root_layout = FloatLayout()
        self.page = BoxLayout(orientation="vertical", spacing=0)
        self.root_layout.add_widget(self.page)
        paint(self, self.root_layout, "bg")
        self.show_login()
        return self.root_layout

    # ---------- общие элементы ----------

    def clear_page(self):
        self.page.clear_widgets()

    def label(self, text, size=14, color=None, bold=False, height=None, halign="left", markup=False):
        lbl = Label(
            text=str(text),
            color=color or self.colors["text"],
            font_size=dp(size),
            bold=bold,
            size_hint_y=None,
            height=dp(height) if height else dp(size * 2.1),
            halign=halign,
            valign="middle",
            markup=markup,
        )
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        return lbl

    def eyebrow(self, text):
        return self.label(str(text).upper(), 11, self.colors["accent_text"], bold=True, height=22)

    def divider(self):
        line = Widget(size_hint_y=None, height=dp(1))
        paint(self, line, "divider")
        return line

    def accent_bar(self):
        bar = Widget(size_hint=(None, None), size=(dp(36), dp(3)))
        paint(self, bar, "accent")
        return bar

    def header(self, authenticated=False):
        row = BoxLayout(size_hint_y=None, height=dp(56), padding=[dp(10), dp(6)], spacing=dp(4))
        if authenticated:
            home = AromaButton(self, variant="ghost", text="ГЛАВНАЯ", size_hint_x=None,
                               width=dp(92), height=dp(44))
            home.bind(on_press=lambda *_: self.show_home())
            row.add_widget(home)
        else:
            row.add_widget(Widget(size_hint_x=None, width=dp(92)))
        row.add_widget(Widget())
        brand = self.label("AROMASYS", 18, bold=True, height=40, halign="center")
        brand.size_hint_x = None
        brand.width = dp(140)
        row.add_widget(brand)
        row.add_widget(Widget())
        row.add_widget(Widget(size_hint_x=None, width=dp(92)))
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(57))
        box.add_widget(row)
        box.add_widget(self.divider())
        return box

    def scroll_content(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(orientation="vertical", padding=[dp(20), dp(18), dp(20), dp(30)],
                            spacing=dp(14), size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        return scroll, content

    def toast(self, message, seconds=2.5):
        card = Card(self, key="primary", radius=8, size_hint=(None, None),
                    size=(dp(320), dp(56)), pos_hint={"center_x": 0.5, "y": 0.03}, padding=dp(12))
        lbl = Label(text=str(message), color=self.colors["primary_text"], font_size=dp(13),
                    halign="center", valign="middle")
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        card.add_widget(lbl)
        self.root_layout.add_widget(card)
        Clock.schedule_once(lambda _dt: self.root_layout.remove_widget(card)
                            if card.parent else None, seconds)

    def theme_button(self):
        button = AromaButton(self, variant="ghost", text=self.theme_button_text(), height=42)
        button.bind(on_press=self.set_theme)
        return button

    def theme_button_text(self):
        return "Тёмная тема" if self.theme_name == "light" else "Светлая тема"

    def set_theme(self, *_):
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        self.colors = self.THEMES[self.theme_name]
        paint(self, self.root_layout, "bg")
        screen = self.active_screen
        saved_scroll = self.current_scroll.scroll_y if self.current_scroll is not None else 1.0
        if screen == "login":
            self.show_login()
        elif screen == "registration":
            self.show_registration()
        elif screen == "home":
            self.show_home(self.current_username, self.current_email)
        elif screen == "catalog":
            self.show_catalog(self.catalog_gender, self.catalog_query, reload_data=False)
            Clock.schedule_once(lambda _dt: setattr(self.catalog_scroll, "scroll_y", saved_scroll), 0.15)
        elif screen == "favorites":
            self.show_favorites(reload_data=False)
            Clock.schedule_once(lambda _dt: setattr(self.favorites_scroll, "scroll_y", saved_scroll), 0.15)
        elif screen == "detail" and self.selected_product:
            self.show_product_detail(self.selected_product)
        elif screen == "profile":
            self.show_profile()
        elif screen == "orders":
            self.show_orders()
        else:
            self.show_home(self.current_username, self.current_email)

    def confirm(self, title, message, on_confirm):
        view = ModalView(size_hint=(0.88, None), height=dp(230), auto_dismiss=False,
                         background_color=(0, 0, 0, 0.45))
        panel = Card(self, key="panel", radius=12, orientation="vertical",
                     padding=dp(18), spacing=dp(12))
        panel.add_widget(self.label(title, 19, bold=True, height=34))
        panel.add_widget(self.label(message, 14, self.colors["muted"], height=55))
        row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        cancel = AromaButton(self, variant="soft", text="ОТМЕНА", height=46)
        confirm = AromaButton(self, variant="danger", text="ПОДТВЕРДИТЬ", height=46)
        cancel.bind(on_press=lambda *_: view.dismiss())

        def accepted(*_):
            view.dismiss()
            on_confirm()

        confirm.bind(on_press=accepted)
        row.add_widget(cancel)
        row.add_widget(confirm)
        panel.add_widget(row)
        view.add_widget(panel)
        view.open()

    def async_request(self, method, path, *, params=None, json_data=None,
                      on_success=None, on_error=None, timeout=8):
        """Выполняет HTTP-запрос в отдельном потоке, UI обновляет только главный поток."""
        def worker():
            try:
                headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
                response = requests.request(method, f"{API_URL}{path}", params=params,
                                             json=json_data, headers=headers, timeout=timeout)
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                if not 200 <= response.status_code < 300:
                    message = (payload.get("error") or payload.get("message")
                               if isinstance(payload, dict) else None)
                    message = message or f"Ошибка сервера ({response.status_code})"
                    Clock.schedule_once(lambda _dt: on_error(message) if on_error else None, 0)
                    return
                Clock.schedule_once(lambda _dt: on_success(payload, response.status_code)
                                    if on_success else None, 0)
            except requests.RequestException:
                Clock.schedule_once(lambda _dt: on_error("Нет соединения с сервером. Проверь Flask.")
                                    if on_error else None, 0)

        threading.Thread(target=worker, daemon=True).start()

    def set_status(self, widget, message, error=True):
        if not widget:
            return
        widget.text = message
        widget.color = self.colors["danger"] if error else self.colors["accent_text"]

    # ---------- регистрация и авторизация ----------

    def show_login(self, *args):
        self.active_screen = "login"
        self.clear_page()
        self.page.add_widget(self.header())
        scroll, content = self.scroll_content()
        content.add_widget(self.eyebrow("Парфюмерный бутик"))
        content.add_widget(self.label("Вход", 30, bold=True, height=50))
        content.add_widget(self.accent_bar())
        content.add_widget(self.label("Войдите, чтобы продолжить покупки", 14,
                                      self.colors["muted"], height=34))
        self.email = ModernInput(self, hint_text="Email", text=self.auth_values["login_email"])
        self.password = ModernInput(self, hint_text="Пароль", password=True,
                                     text=self.auth_values["login_password"])
        self.email.bind(text=lambda _i, v: self.auth_values.update(login_email=v))
        self.password.bind(text=lambda _i, v: self.auth_values.update(login_password=v))
        content.add_widget(self.email)
        content.add_widget(self.password)
        self.auth_submit_button = AromaButton(self, text="ВОЙТИ")
        self.auth_submit_button.bind(on_press=self.login)
        content.add_widget(self.auth_submit_button)
        register = AromaButton(self, variant="soft", text="СОЗДАТЬ АККАУНТ")
        register.bind(on_press=self.show_registration)
        content.add_widget(register)
        content.add_widget(self.theme_button())
        self.status = self.label("", 13, self.colors["danger"], height=42)
        content.add_widget(self.status)
        self.page.add_widget(scroll)

    def show_registration(self, *args):
        self.active_screen = "registration"
        self.clear_page()
        self.page.add_widget(self.header())
        scroll, content = self.scroll_content()
        content.add_widget(self.eyebrow("Новый покупатель"))
        content.add_widget(self.label("Регистрация", 30, bold=True, height=50))
        content.add_widget(self.accent_bar())
        content.add_widget(self.label("Присоединяйтесь к AromaSys", 14,
                                      self.colors["muted"], height=34))
        self.username = ModernInput(self, hint_text="Имя пользователя",
                                    text=self.auth_values["reg_name"])
        self.email = ModernInput(self, hint_text="Email", text=self.auth_values["reg_email"])
        self.password = ModernInput(self, hint_text="Пароль (минимум 8 символов)", password=True)
        self.username.bind(text=lambda _i, v: self.auth_values.update(reg_name=v))
        self.email.bind(text=lambda _i, v: self.auth_values.update(reg_email=v))
        for field in (self.username, self.email, self.password):
            content.add_widget(field)
        self.auth_submit_button = AromaButton(self, text="ЗАРЕГИСТРИРОВАТЬСЯ")
        self.auth_submit_button.bind(on_press=self.register)
        content.add_widget(self.auth_submit_button)
        back = AromaButton(self, variant="soft", text="УЖЕ ЕСТЬ АККАУНТ? ВОЙТИ")
        back.bind(on_press=self.show_login)
        content.add_widget(back)
        content.add_widget(self.theme_button())
        self.status = self.label("", 13, self.colors["danger"], height=42)
        content.add_widget(self.status)
        self.page.add_widget(scroll)

    def login(self, *_):
        email = self.email.text.strip().lower()
        password = self.password.text
        if not email or not password:
            self.set_status(self.status, "Заполни email и пароль")
            return
        if not EMAIL_RE.match(email):
            self.set_status(self.status, "Введи корректный email")
            return
        self.auth_submit_button.disabled = True
        self.auth_submit_button.text = "ВХОД..."
        self.set_status(self.status, "Проверяем данные...", error=False)

        def success(data, _code):
            self.auth_submit_button.disabled = False
            self.auth_submit_button.text = "ВОЙТИ"
            try:
                self.current_user_id = data["user_id"]
                self.auth_token = data.get("token")
                self.current_username = data["username"]
                self.current_email = data["email"]
            except KeyError:
                self.set_status(self.status, "Сервер вернул неполные данные")
                return
            self.show_home(self.current_username, self.current_email)

        def failure(message):
            self.auth_submit_button.disabled = False
            self.auth_submit_button.text = "ВОЙТИ"
            self.set_status(self.status, message)

        self.async_request("POST", "/login", json_data={"email": email, "password": password},
                           on_success=success, on_error=failure, timeout=8)

    def register(self, *_):
        username = self.username.text.strip()
        email = self.email.text.strip().lower()
        password = self.password.text
        if not username or not email or not password:
            self.set_status(self.status, "Заполни все обязательные поля")
            return
        if len(username) < 2:
            self.set_status(self.status, "Имя должно содержать минимум 2 символа")
            return
        if not EMAIL_RE.match(email):
            self.set_status(self.status, "Введи корректный email")
            return
        if len(password) < 8:
            self.set_status(self.status, "Пароль должен содержать минимум 8 символов")
            return
        self.auth_submit_button.disabled = True
        self.auth_submit_button.text = "СОЗДАНИЕ..."
        self.set_status(self.status, "Создаём аккаунт...", error=False)

        def success(data, _code):
            self.auth_submit_button.disabled = False
            self.auth_submit_button.text = "ЗАРЕГИСТРИРОВАТЬСЯ"
            try:
                self.current_user_id = data["user_id"]
                self.auth_token = data.get("token")
                self.current_username = data["username"]
                self.current_email = data["email"]
            except KeyError:
                self.set_status(self.status, "Сервер вернул неполные данные")
                return
            self.auth_values["login_email"] = self.current_email
            self.show_home(self.current_username, self.current_email)

        def failure(message):
            self.auth_submit_button.disabled = False
            self.auth_submit_button.text = "ЗАРЕГИСТРИРОВАТЬСЯ"
            self.set_status(self.status, message)

        self.async_request("POST", "/register",
                           json_data={"username": username, "email": email, "password": password},
                           on_success=success, on_error=failure, timeout=8)

    def logout(self, *_):
        self.current_username = ""
        self.current_email = ""
        self.current_user_id = None
        self.auth_token = None
        self.local_favorites.clear()
        self.show_login()
        self.toast("Вы вышли из аккаунта")

    # ---------- главное меню и профиль ----------

    def can_manage_products(self):
        """Права управления каталогом выдаются только указанному email владельца."""
        configured_email = str(ADMIN_EMAIL or "").strip().casefold()
        logged_in_email = str(self.current_email or "").strip().casefold()
        return bool(configured_email and logged_in_email == configured_email)

    def show_home(self, username=None, email=None):
        self.active_screen = "home"
        if username is not None:
            self.current_username = username
        if email is not None:
            self.current_email = email
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        content.add_widget(self.label(f"Здравствуйте, {self.current_username}", 22,
                                      bold=True, height=40))
        content.add_widget(self.label(self.current_email, 13, self.colors["muted"], height=26))

        promo = Card(self, key="promo", radius=8, orientation="vertical", padding=dp(20),
                     spacing=dp(6), size_hint_y=None, height=dp(132))
        promo.add_widget(self.label("НОВАЯ КОЛЛЕКЦИЯ", 11, self.colors["promo_text"], bold=True, height=22))
        promo.add_widget(self.label("Подбери аромат\nпод настроение", 22,
                                    self.colors["promo_text"], bold=True, height=60))
        promo.add_widget(self.label("Авторские композиции и бестселлеры", 13,
                                    self.colors["promo_text"], height=26))
        content.add_widget(promo)

        chips_scroll = ScrollView(do_scroll_y=False, size_hint_y=None, height=dp(48), bar_width=0)
        chips_row = BoxLayout(size_hint_x=None, spacing=dp(8), padding=[0, dp(4)])
        chips_row.bind(minimum_width=chips_row.setter("width"))
        for gender in CHIPS:
            chip = AromaButton(self, variant="soft", text=gender, size_hint_x=None,
                               width=dp(118), height=dp(40))
            chip.bind(on_press=lambda _btn, g=gender: self.show_catalog(gender=g, query=""))
            chips_row.add_widget(chip)
        chips_scroll.add_widget(chips_row)
        content.add_widget(chips_scroll)

        content.add_widget(self.eyebrow("Разделы"))
        grid = GridLayout(cols=2, spacing=dp(12), size_hint_y=None)
        grid.bind(minimum_height=grid.setter("height"))
        for title, subtitle in TILES:
            tile = AromaButton(self, variant="panel",
                               text=f"[b]{title}[/b]\n[size=12]{subtitle}[/size]",
                               markup=True, height=dp(104))
            if title == "Каталог":
                tile.bind(on_press=lambda *_: self.show_catalog())
            elif title == "Избранное":
                tile.bind(on_press=lambda *_: self.show_favorites())
            elif title == "Мои заказы":
                tile.bind(on_press=lambda *_: self.show_orders())
            else:
                tile.bind(on_press=lambda *_: self.show_profile())
            grid.add_widget(tile)
        content.add_widget(grid)

        address = Card(self, key="panel", radius=8, orientation="vertical", padding=dp(16),
                       spacing=dp(10), size_hint_y=None, height=dp(168))
        address.add_widget(self.eyebrow("Адрес доставки"))
        self.address_input = ModernInput(self, hint_text="Укажи адрес доставки",
                                          text=self.delivery_address_draft or self.delivery_address)
        self.address_input.bind(text=lambda _i, v: setattr(self, "delivery_address_draft", v))
        address.add_widget(self.address_input)
        save_address = AromaButton(self, variant="soft", text="СОХРАНИТЬ АДРЕС", height=44)
        save_address.bind(on_press=self.save_address)
        address.add_widget(save_address)
        content.add_widget(address)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)

    def save_address(self, *_):
        address = self.address_input.text.strip()
        if len(address) < 5:
            self.toast("Укажи полный адрес доставки")
            return
        self.delivery_address = address
        self.delivery_address_draft = address
        self.show_home(self.current_username, self.current_email)
        self.toast("Адрес сохранён в текущем сеансе")

    def show_profile(self):
        self.active_screen = "profile"
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        content.add_widget(self.eyebrow("Личный кабинет"))
        content.add_widget(self.label("Профиль", 28, bold=True, height=48))
        panel = Card(self, key="panel", radius=10, orientation="vertical", padding=dp(16),
                     spacing=dp(10), size_hint_y=None, height=dp(206))
        panel.add_widget(self.label("Имя пользователя", 12, self.colors["muted"], height=22))
        panel.add_widget(self.label(self.current_username, 17, bold=True, height=28))
        panel.add_widget(self.divider())
        panel.add_widget(self.label("Email", 12, self.colors["muted"], height=22))
        panel.add_widget(self.label(self.current_email, 16, height=28))
        content.add_widget(panel)
        address_panel = Card(self, key="panel", radius=10, orientation="vertical", padding=dp(16),
                             spacing=dp(8), size_hint_y=None, height=dp(104))
        address_panel.add_widget(self.label("Адрес доставки", 12, self.colors["muted"], height=22))
        address_panel.add_widget(self.label(self.delivery_address or "Не указан", 15, height=30))
        content.add_widget(address_panel)
        edit = AromaButton(self, text="РЕДАКТИРОВАТЬ ПРОФИЛЬ")
        edit.bind(on_press=lambda *_: self.show_profile_edit())
        content.add_widget(edit)
        logout = AromaButton(self, variant="danger", text="ВЫЙТИ ИЗ АККАУНТА")
        logout.bind(on_press=lambda *_: self.confirm(
            "Выйти из аккаунта?", "Текущий сеанс будет завершён.", self.logout))
        content.add_widget(logout)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)

    def show_profile_edit(self):
        self.active_screen = "profile_edit"
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        content.add_widget(self.label("Редактирование профиля", 25, bold=True, height=52))
        self.profile_name = ModernInput(self, hint_text="Имя пользователя", text=self.current_username,
                                        disabled=True)
        self.profile_email = ModernInput(self, hint_text="Email", text=self.current_email,
                                         disabled=True)
        self.profile_address = ModernInput(self, hint_text="Адрес доставки", text=self.delivery_address)
        for field in (self.profile_name, self.profile_email, self.profile_address):
            content.add_widget(field)
        self.profile_status = self.label("Имя и email берутся из аккаунта. Здесь редактируется адрес доставки.",
                                         12, self.colors["muted"], height=38)
        content.add_widget(self.profile_status)
        save = AromaButton(self, text="СОХРАНИТЬ ИЗМЕНЕНИЯ")
        save.bind(on_press=self.save_profile)
        content.add_widget(save)
        back = AromaButton(self, variant="soft", text="ОТМЕНА")
        back.bind(on_press=lambda *_: self.show_profile())
        content.add_widget(back)
        self.page.add_widget(scroll)

    def save_profile(self, *_):
        address = self.profile_address.text.strip()
        self.delivery_address = address
        self.delivery_address_draft = address
        self.show_profile()
        self.toast("Профиль обновлён в текущем сеансе")

    def show_orders(self):
        self.active_screen = "orders"
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        content.add_widget(self.label("Мои заказы", 28, bold=True, height=50))
        self.orders_results = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.orders_results.bind(minimum_height=self.orders_results.setter("height"))
        content.add_widget(self.orders_results)
        self.orders_status = self.label("Загружаем заказы...", 13, self.colors["muted"], height=40)
        content.add_widget(self.orders_status)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)
        self.async_request("GET", "/api/orders", on_success=self._orders_loaded,
                           on_error=lambda message: setattr(self.orders_status, "text", message), timeout=10)

    def _orders_loaded(self, data, _code):
        self.orders_results.clear_widgets()
        rows = [x for x in data if x.get("user_id") == self.current_user_id] if isinstance(data, list) else []
        if not rows:
            self.orders_results.add_widget(self.label("Заказов пока нет.", 14, self.colors["muted"], height=50))
        for order in rows:
            panel = Card(self, key="panel", radius=8, orientation="vertical", padding=dp(14),
                         spacing=dp(5), size_hint_y=None, height=dp(92))
            panel.add_widget(self.label(f"Заказ №{order['id']}", 16, bold=True, height=25))
            panel.add_widget(self.label(f"Статус: {order['status']} · Сумма: {order['total_amount']} ₽", 13, height=24))
            self.orders_results.add_widget(panel)
        self.orders_status.text = f"Заказов: {len(rows)}"


    # ---------- каталог, карточка и избранное ----------

    def merged_products(self):
        result = []
        known_ids = set()
        for original in self.catalog_cache:
            item = deepcopy(original)
            sku_id = item.get("sku_id")
            if sku_id in self.deleted_product_ids:
                continue
            item.update(self.product_overrides.get(sku_id, {}))
            result.append(item)
            known_ids.add(sku_id)
        for item in self.local_products:
            if item.get("sku_id") not in self.deleted_product_ids:
                result.append(deepcopy(item))
        return result

    def _filtered_products(self):
        items = self.merged_products()
        if self.catalog_gender:
            items = [x for x in items if x.get("gender") == self.catalog_gender]
        q = self.catalog_query.strip().lower()
        if q:
            items = [x for x in items if q in str(x.get("title", "")).lower()
                     or q in str(x.get("brand", "")).lower()]
        return items

    def show_catalog(self, gender=None, query="", reload_data=True):
        self.active_screen = "catalog"
        self.catalog_gender = gender
        self.catalog_query = query or ""
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        self.current_scroll = scroll
        self.catalog_scroll = scroll
        content.add_widget(self.label("Каталог", 28, bold=True, height=48))
        self.catalog_search_input = ModernInput(self, hint_text="Поиск по названию или бренду",
                                                text=self.catalog_query)
        self.catalog_search_input.bind(text=lambda _i, v: setattr(self, "catalog_query", v))
        content.add_widget(self.catalog_search_input)
        sort_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        sort_labels = {("title", "asc"): "Сортировка: название", ("price", "asc"): "Цена: по возрастанию",
                       ("price", "desc"): "Цена: по убыванию", ("brand", "asc"): "Бренд"}
        self.catalog_sort_spinner = Spinner(text=sort_labels.get((self.catalog_sort, self.catalog_order), "Сортировка: название"),
            values=("Сортировка: название", "Цена: по возрастанию", "Цена: по убыванию", "Бренд"),
            size_hint_x=1, background_normal="", background_color=self.colors["input"],
            color=self.colors["text"])
        self.catalog_sort_spinner.bind(text=self.change_catalog_sort)
        sort_row.add_widget(self.catalog_sort_spinner)
        search_btn = AromaButton(self, variant="soft", text="НАЙТИ", height=44, size_hint_x=None, width=dp(105))
        search_btn.bind(on_press=lambda *_: self.show_catalog(self.catalog_gender,
                                                              self.catalog_search_input.text.strip()))
        sort_row.add_widget(search_btn)
        content.add_widget(sort_row)
        if gender:
            content.add_widget(self.label(f"Фильтр: {gender}", 13, self.colors["muted"], height=24))
        filter_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        all_btn = AromaButton(self, variant="soft", text="Все", height=38)
        all_btn.bind(on_press=lambda *_: self.show_catalog(None, self.catalog_search_input.text.strip()))
        filter_row.add_widget(all_btn)
        for value in GENDERS:
            b = AromaButton(self, variant="soft", text=value, height=38)
            b.bind(on_press=lambda _b, v=value: self.show_catalog(v, self.catalog_search_input.text.strip()))
            filter_row.add_widget(b)
        content.add_widget(filter_row)
        if self.can_manage_products():
            add = AromaButton(self, text="ДОБАВИТЬ ПАРФЮМ")
            add.bind(on_press=lambda *_: self.show_product_form())
            content.add_widget(add)
        self.catalog_results = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.catalog_results.bind(minimum_height=self.catalog_results.setter("height"))
        content.add_widget(self.catalog_results)
        self.catalog_status = self.label("Загружаем каталог...", 13, self.colors["muted"], height=42)
        content.add_widget(self.catalog_status)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)

        if reload_data:
            self.catalog_status.text = "Загружаем каталог..."
            self.async_request("GET", "/catalog",
                               params={"gender": gender, "q": self.catalog_query, "sort": self.catalog_sort, "order": self.catalog_order},
                               on_success=self._catalog_loaded, on_error=self._catalog_failed, timeout=10)
        else:
            self.render_catalog_items()

    def change_catalog_sort(self, _spinner, value):
        mapping = {"Сортировка: название": ("title", "asc"),
                   "Цена: по возрастанию": ("price", "asc"),
                   "Цена: по убыванию": ("price", "desc"),
                   "Бренд": ("brand", "asc")}
        self.catalog_sort, self.catalog_order = mapping.get(value, ("title", "asc"))

    def _catalog_loaded(self, data, _code):
        if not isinstance(data, (list, dict)):
            self._catalog_failed("Сервер вернул неверный формат каталога")
            return
        self.catalog_cache = data.get("items", []) if isinstance(data, dict) else data
        if self.active_screen == "catalog":
            self.render_catalog_items()

    def _catalog_failed(self, message):
        if self.active_screen != "catalog":
            self.toast(message)
            return
        self.catalog_results.clear_widgets()
        self.catalog_status.text = message
        self.catalog_status.color = self.colors["danger"]
        # Локальные изменения остаются доступны даже при временной ошибке API.
        local_items = self._filtered_products()
        for item in local_items:
            self.catalog_results.add_widget(self.product_card(item))

    def render_catalog_items(self):
        if not hasattr(self, "catalog_results"):
            return
        self.catalog_results.clear_widgets()
        items = self._filtered_products()
        if not items:
            self.catalog_results.add_widget(self.label("По этому запросу ничего не найдено.",
                                                        14, self.colors["muted"], height=58))
        for item in items:
            self.catalog_results.add_widget(self.product_card(item))
        if hasattr(self, "catalog_status"):
            self.catalog_status.text = f"Найдено товаров: {len(items)}"
            self.catalog_status.color = self.colors["muted"]

    def product_card(self, item, favorite_screen=False):
        card = Card(self, key="panel", radius=10, orientation="horizontal",
                    padding=[dp(10), dp(10), dp(12), dp(10)], spacing=dp(12),
                    size_hint_y=None, height=dp(142))
        img_box = BoxLayout(size_hint=(None, None), size=(dp(100), dp(118)))
        img_url = item.get("image_url")
        if img_url:
            if img_url.startswith("/"):
                img_url = f"{API_URL}{img_url}"
            img_box.add_widget(AsyncImage(source=img_url, size_hint=(1, 1),
                                          allow_stretch=True, keep_ratio=True))
        else:
            img_box.add_widget(self.label("Нет фото", 11, self.colors["muted"], halign="center"))
        card.add_widget(img_box)
        right = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        right.add_widget(self.eyebrow(item.get("brand", "Бренд")))
        right.add_widget(self.label(item.get("title", "Без названия"), 15, bold=True, height=25))
        details = f"{item.get('concentration', '')} · {item.get('volume_ml', '')} мл · {item.get('gender', '')}"
        right.add_widget(self.label(details, 10, self.colors["muted"], height=20))
        price_val = item.get("price", 0)
        try:
            price = f"{float(price_val):,.0f} ₽".replace(",", " ")
        except (TypeError, ValueError):
            price = "Цена не указана"
        right.add_widget(self.label(f"{price}  ·  остаток {item.get('stock', 0)}", 12, bold=True, height=21))
        actions = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
        details_btn = AromaButton(self, variant="soft", text="ОТКРЫТЬ", height=32)
        details_btn.bind(on_press=lambda *_args, p=deepcopy(item): self.show_product_detail(p))
        actions.add_widget(details_btn)
        if favorite_screen:
            fav_btn = AromaButton(self, variant="soft", text="УБРАТЬ", height=32)
            fav_btn.bind(on_press=lambda *_args, p=deepcopy(item): self.delete_favorite(p))
        else:
            fav_btn = AromaButton(self, variant="soft", text="В ИЗБРАННОЕ", height=32)
            fav_btn.bind(on_press=lambda *_args, p=deepcopy(item): self.add_favorite(p))
        actions.add_widget(fav_btn)
        right.add_widget(actions)
        card.add_widget(right)
        return card

    def open_product_detail(self, item, origin="catalog"):
        self.detail_return_screen = origin
        if self.current_scroll is not None:
            self.detail_return_scroll_y = self.current_scroll.scroll_y
        self.show_product_detail(item)

    def return_to_detail_origin(self):
        offset = self.detail_return_scroll_y
        if self.detail_return_screen == "favorites":
            self.show_favorites(reload_data=False)
            Clock.schedule_once(lambda _dt: setattr(self.favorites_scroll, "scroll_y", offset), 0.15)
        else:
            self.show_catalog(self.catalog_gender, self.catalog_query, reload_data=False)
            Clock.schedule_once(lambda _dt: setattr(self.catalog_scroll, "scroll_y", offset), 0.15)

    def show_product_detail(self, item):
        self.active_screen = "detail"
        self.selected_product = deepcopy(item)
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        content.add_widget(self.label(item.get("title", "Парфюм"), 27, bold=True, height=50))
        image_url = item.get("image_url")
        if image_url:
            if image_url.startswith("/"):
                image_url = f"{API_URL}{image_url}"
            image = AsyncImage(source=image_url, size_hint_y=None, height=dp(230),
                               allow_stretch=True, keep_ratio=True)
            content.add_widget(image)
        else:
            image_placeholder = Card(self, key="panel", radius=10, size_hint_y=None, height=dp(150))
            image_placeholder.add_widget(self.label("Фотография не добавлена", 14,
                                                     self.colors["muted"], halign="center"))
            content.add_widget(image_placeholder)
        info = Card(self, key="panel", radius=10, orientation="vertical", padding=dp(16),
                    spacing=dp(8), size_hint_y=None, height=dp(250))
        info.add_widget(self.label(f"Бренд: {item.get('brand', 'Не указан')}", 15, height=27))
        info.add_widget(self.label(f"Пол: {item.get('gender', 'Не указан')}", 14, height=25))
        info.add_widget(self.label(f"Концентрация: {item.get('concentration', 'Не указана')}", 14, height=25))
        info.add_widget(self.label(f"Объём: {item.get('volume_ml', 0)} мл", 14, height=25))
        info.add_widget(self.label(f"Год выпуска: {item.get('release_year', 'Не указан')}", 14, height=25))
        info.add_widget(self.label(f"Остаток: {item.get('stock', 0)}", 14, height=25))
        try:
            price = f"{float(item.get('price', 0)):,.0f} ₽".replace(",", " ")
        except (TypeError, ValueError):
            price = "Цена не указана"
        info.add_widget(self.label(f"Цена: {price}", 18, bold=True, height=30))
        content.add_widget(info)
        favorite = AromaButton(self, variant="soft", text="ДОБАВИТЬ В ИЗБРАННОЕ")
        favorite.bind(on_press=lambda *_: self.add_favorite(self.selected_product))
        content.add_widget(favorite)
        order_btn = AromaButton(self, text="ОФОРМИТЬ ЗАКАЗ")
        order_btn.bind(on_press=lambda *_: self.order_product(self.selected_product))
        content.add_widget(order_btn)
        if self.can_manage_products():
            edit = AromaButton(self, text="РЕДАКТИРОВАТЬ")
            edit.bind(on_press=lambda *_: self.show_product_form(self.selected_product))
            content.add_widget(edit)
            delete = AromaButton(self, variant="danger", text="УДАЛИТЬ ТОВАР")
            delete.bind(on_press=lambda *_: self.confirm(
                "Удалить товар?", "Товар будет удалён из базы данных, если он не входит в существующий заказ.",
                lambda: self.delete_product(self.selected_product)))
            content.add_widget(delete)
        back = AromaButton(self, variant="ghost",
                           text="НАЗАД В ИЗБРАННОЕ" if self.detail_return_screen == "favorites" else "НАЗАД К КАТАЛОГУ")
        back.bind(on_press=lambda *_: self.return_to_detail_origin())
        content.add_widget(back)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)

    def order_product(self, item):
        if not self.current_user_id:
            self.toast("Сначала войди в аккаунт")
            return
        try:
            amount = float(item.get("price", 0))
            sku_id = int(item.get("sku_id"))
        except (TypeError, ValueError):
            self.toast("Не удалось определить товар и цену")
            return
        if amount <= 0:
            self.toast("Некорректная цена товара")
            return
        payload = {"user_id": self.current_user_id, "status": "new", "total_amount": amount}
        self.toast("Создаём заказ...")
        def order_created(data, _code):
            order_id = data.get("id")
            if not order_id:
                self.toast("Сервер не вернул номер заказа")
                return
            item_payload = {"order_id": order_id, "sku_id": sku_id,
                            "price": amount, "quantity": 1}
            self.async_request("POST", "/api/order-items", json_data=item_payload,
                on_success=lambda _d, _c: self.toast(f"Заказ №{order_id} оформлен"),
                on_error=lambda message: self.toast(f"Заказ создан, но позиция не добавлена: {message}"), timeout=12)
        self.async_request("POST", "/api/orders", json_data=payload,
                           on_success=order_created, on_error=self.toast, timeout=12)

    def show_product_form(self, item=None):
        if not self.can_manage_products():
            self.toast("Управление каталогом доступно только владельцу")
            return
        self.active_screen = "product_form"
        self.product_form_item = deepcopy(item) if item else None
        item = item or {}
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        is_edit = bool(self.product_form_item)
        content.add_widget(self.label("Редактирование товара" if is_edit else "Новый товар",
                                      26, bold=True, height=52))
        self.product_brand = ModernInput(self, hint_text="Бренд *", text=str(item.get("brand", "")))
        self.product_title = ModernInput(self, hint_text="Название парфюма *", text=str(item.get("title", "")))
        self.product_gender = Spinner(text=item.get("gender", GENDERS[0]), values=GENDERS,
                                      size_hint_y=None, height=dp(52), background_normal="",
                                      background_color=self.colors["input"], color=self.colors["text"])
        self.product_concentration = Spinner(text=item.get("concentration", CONCENTRATIONS[2]),
                                             values=CONCENTRATIONS, size_hint_y=None, height=dp(52),
                                             background_normal="", background_color=self.colors["input"],
                                             color=self.colors["text"])
        self.product_volume = ModernInput(self, hint_text="Объём в мл *", input_filter="int",
                                          text=str(item.get("volume_ml", "")))
        self.product_price = ModernInput(self, hint_text="Цена в рублях *", input_filter="float",
                                         text=str(item.get("price", "")))
        self.product_stock = ModernInput(self, hint_text="Количество на складе *", input_filter="int",
                                         text=str(item.get("stock", "0")))
        self.product_year = ModernInput(self, hint_text="Год выпуска *", input_filter="int",
                                        text=str(item.get("release_year", "2026")))
        for widget in (self.product_brand, self.product_title, self.product_gender,
                       self.product_concentration, self.product_volume, self.product_price,
                       self.product_stock, self.product_year):
            content.add_widget(widget)
        content.add_widget(self.label("* Обязательные поля. Изменения сохраняются в PostgreSQL через API.",
                                      12, self.colors["muted"], height=45))
        self.product_form_status = self.label("", 13, self.colors["danger"], height=36)
        content.add_widget(self.product_form_status)
        save = AromaButton(self, text="СОХРАНИТЬ ТОВАР")
        save.bind(on_press=self.save_product)
        content.add_widget(save)
        cancel = AromaButton(self, variant="soft", text="ОТМЕНА")
        cancel.bind(on_press=lambda *_: self._cancel_product_form())
        content.add_widget(cancel)
        self.page.add_widget(scroll)

    def _cancel_product_form(self):
        if self.product_form_item:
            self.show_product_detail(self.product_form_item)
        else:
            self.show_catalog(self.catalog_gender, self.catalog_query, reload_data=False)

    def save_product(self, *_):
        if not self.can_manage_products():
            self.toast("Управление каталогом доступно только владельцу")
            return
        brand = self.product_brand.text.strip()
        title = self.product_title.text.strip()
        volume_text = self.product_volume.text.strip()
        price_text = self.product_price.text.strip().replace(",", ".")
        stock_text = self.product_stock.text.strip()
        year_text = self.product_year.text.strip()
        if not all((brand, title, volume_text, price_text, stock_text, year_text)):
            self.set_status(self.product_form_status, "Заполни все обязательные поля")
            return
        try:
            volume, price, stock, year = int(volume_text), float(price_text), int(stock_text), int(year_text)
        except ValueError:
            self.set_status(self.product_form_status, "Проверь числовые поля")
            return
        if not 1 <= volume <= 1000 or price <= 0 or stock < 0 or not 1900 <= year <= 2100:
            self.set_status(self.product_form_status, "Проверь объём, цену, остаток и год выпуска")
            return
        payload = {"brand": brand, "title": title, "gender": self.product_gender.text,
                   "concentration": self.product_concentration.text, "release_year": year,
                   "volume_ml": volume, "price": price, "stock": stock}
        existing = self.product_form_item
        button_text = "СОХРАНИТЬ ТОВАР"
        for child in self.page.walk():
            if isinstance(child, AromaButton) and child.text == button_text:
                child.disabled = True
        def success(data, _code):
            self.catalog_cache = [x for x in self.catalog_cache if x.get("sku_id") != data.get("sku_id")]
            if existing:
                self.catalog_cache = [x for x in self.catalog_cache if x.get("sku_id") != existing.get("sku_id")]
                self.catalog_cache.append(data)
            else:
                self.catalog_cache.append(data)
            self.toast("Товар сохранён в PostgreSQL")
            if existing:
                self.show_product_detail(data)
            else:
                self.show_catalog(self.catalog_gender, self.catalog_query, reload_data=True)
        def failure(message):
            self.set_status(self.product_form_status, message)
            self.toast(message)
        if existing:
            sku_id = existing.get("sku_id")
            self.async_request("PATCH", f"/api/catalog-items/{sku_id}", json_data=payload,
                               on_success=success, on_error=failure, timeout=12)
        else:
            self.async_request("POST", "/api/catalog-items", json_data=payload,
                               on_success=success, on_error=failure, timeout=12)

    def delete_product(self, item):
        if not self.can_manage_products():
            self.toast("Управление каталогом доступно только владельцу")
            return
        sku_id = item.get("sku_id")
        if not sku_id:
            self.toast("Не удалось определить товар")
            return
        def success(_data, _code):
            self.catalog_cache = [x for x in self.catalog_cache if x.get("sku_id") != sku_id]
            self.cached_favorites = [x for x in getattr(self, "cached_favorites", []) if x.get("sku_id") != sku_id]
            self.toast("Товар удалён из PostgreSQL")
            self.show_catalog(self.catalog_gender, self.catalog_query, reload_data=True)
        self.async_request("DELETE", f"/api/catalog-items/{sku_id}",
                           on_success=success, on_error=self.toast, timeout=12)

    def show_favorites(self, reload_data=True):
        self.active_screen = "favorites"
        self.clear_page()
        self.page.add_widget(self.header(authenticated=True))
        scroll, content = self.scroll_content()
        self.current_scroll = scroll
        self.favorites_scroll = scroll
        content.add_widget(self.label("Избранное", 28, bold=True, height=48))
        self.favorites_results = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.favorites_results.bind(minimum_height=self.favorites_results.setter("height"))
        content.add_widget(self.favorites_results)
        self.favorites_status = self.label("Загружаем избранное...", 13,
                                           self.colors["muted"], height=40)
        content.add_widget(self.favorites_status)
        content.add_widget(self.theme_button())
        self.page.add_widget(scroll)
        if reload_data:
            if not self.current_user_id:
                self._favorites_failed("Сначала войди в аккаунт")
                return
            self.async_request("GET", f"/favorites/{self.current_user_id}",
                               on_success=self._favorites_loaded,
                               on_error=self._favorites_failed, timeout=10)
        else:
            self.render_favorites(self.cached_favorites if hasattr(self, "cached_favorites") else [])

    def _favorites_loaded(self, data, _code):
        self.cached_favorites = data if isinstance(data, list) else []
        if self.active_screen == "favorites":
            self.render_favorites(self.cached_favorites)

    def _favorites_failed(self, message):
        if self.active_screen != "favorites":
            self.toast(message)
            return
        self.favorites_status.text = message
        self.favorites_status.color = self.colors["danger"]
        self.render_favorites([])

    def render_favorites(self, api_items):
        self.favorites_results.clear_widgets()
        items = list(api_items)
        for sku_id in self.local_favorites:
            found = next((p for p in self.merged_products() if p.get("sku_id") == sku_id), None)
            if found and all(x.get("sku_id") != sku_id for x in items):
                items.append(found)
        items = [x for x in items if x.get("sku_id") not in self.deleted_product_ids]
        if not items:
            self.favorites_results.add_widget(self.label("Здесь пока нет сохранённых ароматов.",
                                                          14, self.colors["muted"], height=55))
        for item in items:
            self.favorites_results.add_widget(self.product_card(item, favorite_screen=True))
        if hasattr(self, "favorites_status"):
            self.favorites_status.text = f"Сохранено товаров: {len(items)}"
            self.favorites_status.color = self.colors["muted"]

    def add_favorite(self, item):
        sku_id = item.get("sku_id")
        if sku_id is None:
            self.toast("Не удалось определить товар")
            return
        if item.get("is_local") or sku_id < 0:
            self.local_favorites.add(sku_id)
            self.toast("Добавлено в избранное в текущем сеансе")
            return
        if not self.current_user_id:
            self.toast("Сначала войди в аккаунт")
            return

        def success(_data, _code):
            self.toast("Добавлено в избранное")

        self.toast("Добавляем в избранное...")
        self.async_request("POST", "/favorites", json_data={"user_id": self.current_user_id,
                                                                 "sku_id": sku_id},
                           on_success=success, on_error=self.toast, timeout=8)

    def delete_favorite(self, item):
        def accepted():
            sku_id = item.get("sku_id")
            if item.get("is_local") or (isinstance(sku_id, int) and sku_id < 0):
                self.local_favorites.discard(sku_id)
                self.toast("Удалено из избранного")
                if self.active_screen == "favorites":
                    self.render_favorites(getattr(self, "cached_favorites", []))
                return
            if not self.current_user_id:
                self.toast("Сначала войди в аккаунт")
                return

            def success(_data, _code):
                self.cached_favorites = [x for x in getattr(self, "cached_favorites", [])
                                         if x.get("sku_id") != sku_id]
                if self.active_screen == "favorites":
                    self.render_favorites(self.cached_favorites)
                self.toast("Удалено из избранного")

            self.toast("Удаляем из избранного...")
            self.async_request("DELETE", f"/favorites/{self.current_user_id}/{sku_id}",
                               on_success=success, on_error=self.toast, timeout=8)

        self.confirm("Убрать из избранного?", "Аромат будет удалён из сохранённого списка.", accepted)


if __name__ == "__main__":
    AromaSysApp().run()
