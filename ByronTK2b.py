#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ByronTK — RetroWave Edition (v2a - Memetic Patch)
=================================================
Interface graphique pour le moteur de scan Byron (Byron5a.py).
Cette version intègre les nouvelles options :
• Mode --noproxy (scan direct furtif)
• Mode --memetic-chain (Protocole Dashem44 pour Proteus-Lab)
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, font as tkfont
import threading
import queue
import logging
import re
import json
import os
import sys
import time
from datetime import datetime

# ═════════════════════════════════════════════════════════════
# IMPORT DU MOTEUR DE SCAN
# ═════════════════════════════════════════════════════════════
try:
    from Byron5b import SecurityTester, AggressionLevel, ApiType
except ImportError:
    _root = tk.Tk()
    _root.withdraw()
    messagebox.showerror(
        "Module manquant",
        "Impossible d'importer Byron5a.py.\n"
        "Assurez-vous que ce fichier se trouve dans le même répertoire "
        "que ByronTK2a.py."
    )
    sys.exit(1)

# Correctif mineur : get_request_delay / get_payload_count doivent
# exister sur l'énumération AggressionLevel (absents dans certaines
# versions de Byron5a.py).
if not hasattr(AggressionLevel, "get_request_delay"):
    def _get_delay(self):
        return {"low": 2.0, "medium": 1.0, "high": 0.5}[self.value]
    def _get_count(self):
        return {"low": 3, "medium": 5, "high": -1}[self.value]
    AggressionLevel.get_request_delay = _get_delay
    AggressionLevel.get_payload_count = _get_count

# ═════════════════════════════════════════════════════════════
# PALETTE & TYPOGRAPHIE
# ═════════════════════════════════════════════════════════════
class Palette:
    BG          = "#0a0a14"
    BG_HEADER_A = "#150a2e"
    BG_HEADER_B = "#0a0a1c"
    BG_PANEL    = "#11111e"
    BG_CARD     = "#161628"
    BG_INPUT    = "#0d0d1a"
    BORDER      = "#28284a"
    BORDER_SOFT = "#1c1c34"
    CYAN        = "#00f3ff"
    MAGENTA     = "#ff2fd4"
    PINK        = "#ff5f9e"
    PURPLE      = "#a855f7"
    YELLOW      = "#ffd166"
    RED         = "#ff4d6d"
    GREEN       = "#3ddc97"
    TEXT        = "#e4e4ff"
    TEXT_DIM    = "#7d7da3"
    TEXT_FAINT  = "#4d4d70"

    @staticmethod
    def _pick_font(candidates, fallback):
        try:
            available = set(tkfont.families())
        except tk.TclError:
            return fallback
        for name in candidates:
            if name in available:
                return name
        return fallback

class Fonts:
    MONO = "Consolas"
    UI = "Segoe UI"

    @classmethod
    def resolve(cls):
        cls.MONO = Palette._pick_font(
            ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Ubuntu Mono", "Courier New"],
            "Courier"
        )
        cls.UI = Palette._pick_font(
            ["Segoe UI", "Ubuntu", "Helvetica Neue", "DejaVu Sans", "Arial"],
            "Helvetica"
        )

# ═════════════════════════════════════════════════════════════
# PETITS COMPOSANTS RÉUTILISABLES
# ═════════════════════════════════════════════════════════════
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, _event=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.configure(bg=Palette.MAGENTA)
        label = tk.Label(
            self.tip, text=self.text, justify="left",
            bg=Palette.BG_CARD, fg=Palette.CYAN,
            font=(Fonts.UI, 9), padx=8, pady=4,
            highlightthickness=1, highlightbackground=Palette.MAGENTA,
        )
        label.pack(padx=1, pady=1)

    def _hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class StatusPill(tk.Canvas):
    STATES = {
        "idle":     (Palette.TEXT_FAINT, "IDLE"),
        "scanning": (Palette.CYAN, "SCANNING"),
        "done":     (Palette.GREEN, "COMPLETE"),
        "aborted":  (Palette.RED, "ABORTED"),
        "error":    (Palette.RED, "ERROR"),
    }

    def __init__(self, parent, **kwargs):
        super().__init__(parent, width=150, height=26, bg=Palette.BG_HEADER_B,
                         highlightthickness=0, **kwargs)
        self.dot = self.create_oval(4, 9, 16, 21, fill=Palette.TEXT_FAINT, outline="")
        self.label = self.create_text(24, 13, anchor="w", text="IDLE",
                                      fill=Palette.TEXT_DIM,
                                      font=(Fonts.MONO, 10, "bold"))
        self._blink_job = None
        self._blink_on = True

    def set_state(self, state):
        color, text = self.STATES.get(state, self.STATES["idle"])
        self.itemconfig(self.dot, fill=color)
        self.itemconfig(self.label, text=text, fill=color)
        if self._blink_job:
            self.after_cancel(self._blink_job)
            self._blink_job = None
        if state == "scanning":
            self._blink(color)

    def _blink(self, color):
        self._blink_on = not self._blink_on
        self.itemconfig(self.dot, fill=color if self._blink_on else Palette.BG_PANEL)
        self._blink_job = self.after(600, lambda: self._blink(color))

# ═════════════════════════════════════════════════════════════
# HANDLER DE LOG TKINTER (THREAD-SAFE)
# ═════════════════════════════════════════════════════════════
class TkinterLogHandler(logging.Handler):
    ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.ANSI_RE.sub("", self.format(record))
        self.log_queue.put((msg, record.levelno))

# ═════════════════════════════════════════════════════════════
# APPLICATION PRINCIPALE
# ═════════════════════════════════════════════════════════════
class ByronApp:
    API_TYPES = ["rest", "graphql", "generic", "mossbauer"]
    AGGRESSION_LEVELS = ["low", "medium", "high"]

    def __init__(self, root):
        self.root = root
        Fonts.resolve()
        self.root.title("⚡ BYRON // MCP & API SECURITY SCANNER")
        self.root.geometry("1360x860")
        self.root.minsize(1040, 680)
        self.root.configure(bg=Palette.BG)
        
        self.log_queue = queue.Queue()
        self.scan_thread = None
        self.stop_event = threading.Event()
        self.scan_start_time = None
        self.autoscroll = tk.BooleanVar(value=True)
        self.min_log_level = tk.StringVar(value="DEBUG")
        self.vars = {}
        self.field_errors = {}
        
        self._setup_style()
        self._build_menu()
        self._build_layout()
        self._setup_logging_capture()
        
        self.root.after(100, self._poll_log_queue)
        self.root.after(500, self._tick_elapsed)

    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(".", background=Palette.BG_PANEL, foreground=Palette.TEXT, font=(Fonts.UI, 10))
        style.configure("Card.TFrame", background=Palette.BG_CARD)
        style.configure("Panel.TFrame", background=Palette.BG_PANEL)
        style.configure("Header.TFrame", background=Palette.BG_HEADER_B)
        style.configure("CardTitle.TLabel", background=Palette.BG_CARD, foreground=Palette.MAGENTA, font=(Fonts.UI, 11, "bold"))
        style.configure("Field.TLabel", background=Palette.BG_CARD, foreground=Palette.TEXT_DIM, font=(Fonts.UI, 9, "bold"))
        style.configure("Hint.TLabel", background=Palette.BG_CARD, foreground=Palette.TEXT_FAINT, font=(Fonts.UI, 8))
        style.configure("Brand.TLabel", background=Palette.BG_HEADER_B, foreground=Palette.MAGENTA, font=(Fonts.MONO, 20, "bold"))
        style.configure("Tag.TLabel", background=Palette.BG_HEADER_B, foreground=Palette.CYAN, font=(Fonts.MONO, 9))
        style.configure("TEntry", fieldbackground=Palette.BG_INPUT, foreground=Palette.TEXT, insertcolor=Palette.MAGENTA,
                        bordercolor=Palette.BORDER, lightcolor=Palette.BORDER, darkcolor=Palette.BORDER, borderwidth=1,
                        font=(Fonts.MONO, 10), padding=6)
        style.map("TEntry", bordercolor=[("focus", Palette.CYAN)], lightcolor=[("focus", Palette.CYAN)])
        style.configure("Error.TEntry", bordercolor=Palette.RED, lightcolor=Palette.RED, darkcolor=Palette.RED)
        style.configure("TCombobox", fieldbackground=Palette.BG_INPUT, background=Palette.BG_INPUT, foreground=Palette.TEXT,
                        arrowcolor=Palette.MAGENTA, bordercolor=Palette.BORDER, font=(Fonts.MONO, 10), padding=5)
        style.map("TCombobox", fieldbackground=[("readonly", Palette.BG_INPUT)], foreground=[("readonly", Palette.TEXT)])
        style.configure("TCheckbutton", background=Palette.BG_CARD, foreground=Palette.TEXT, font=(Fonts.UI, 10))
        style.map("TCheckbutton", background=[("active", Palette.BG_CARD)])
        style.configure("TNotebook", background=Palette.BG_PANEL, borderwidth=0)
        style.configure("TNotebook.Tab", background=Palette.BG_PANEL, foreground=Palette.TEXT_DIM, padding=(16, 8),
                        font=(Fonts.UI, 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", Palette.BG_CARD)], foreground=[("selected", Palette.CYAN)])
        style.configure("Primary.TButton", background="#2a0a4a", foreground=Palette.CYAN, font=(Fonts.UI, 11, "bold"),
                        borderwidth=0, padding=(14, 10))
        style.map("Primary.TButton", background=[("active", "#3a1264"), ("disabled", "#1a1a2e")],
                  foreground=[("disabled", Palette.TEXT_FAINT)])
        style.configure("Danger.TButton", background="#3a0a14", foreground=Palette.RED, font=(Fonts.UI, 11, "bold"),
                        borderwidth=0, padding=(14, 10))
        style.map("Danger.TButton", background=[("active", "#5a0f1e"), ("disabled", "#1a1a2e")],
                  foreground=[("disabled", Palette.TEXT_FAINT)])
        style.configure("Ghost.TButton", background=Palette.BG_CARD, foreground=Palette.TEXT_DIM, font=(Fonts.UI, 9),
                        borderwidth=1, padding=(8, 5))
        style.map("Ghost.TButton", background=[("active", Palette.BORDER_SOFT)], foreground=[("active", Palette.CYAN)])
        style.configure("TScrollbar", background=Palette.BG_PANEL, troughcolor=Palette.BG, bordercolor=Palette.BG,
                        arrowcolor=Palette.MAGENTA)
        style.configure("Progress.Horizontal.TProgressbar", troughcolor=Palette.BG_INPUT, background=Palette.MAGENTA,
                        bordercolor=Palette.BG_INPUT, lightcolor=Palette.MAGENTA, darkcolor=Palette.MAGENTA)

    def _build_menu(self):
        menubar = tk.Menu(self.root, bg=Palette.BG_PANEL, fg=Palette.TEXT,
                          activebackground=Palette.BG_CARD, activeforeground=Palette.CYAN, borderwidth=0)
        file_menu = tk.Menu(menubar, tearoff=0, bg=Palette.BG_CARD, fg=Palette.TEXT,
                            activebackground=Palette.BORDER_SOFT, activeforeground=Palette.CYAN)
        file_menu.add_command(label="📂  Charger une configuration…", command=self.load_json_config)
        file_menu.add_command(label="💾  Enregistrer la configuration…", command=self.save_json_config)
        file_menu.add_separator()
        file_menu.add_command(label="✖  Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=file_menu)
        
        log_menu = tk.Menu(menubar, tearoff=0, bg=Palette.BG_CARD, fg=Palette.TEXT,
                           activebackground=Palette.BORDER_SOFT, activeforeground=Palette.CYAN)
        log_menu.add_command(label="🧹  Vider la console", command=self.clear_log)
        log_menu.add_command(label="📋  Copier la console", command=self.copy_log)
        log_menu.add_command(label="⬇  Exporter la console…", command=self.export_log)
        menubar.add_cascade(label="Console", menu=log_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0, bg=Palette.BG_CARD, fg=Palette.TEXT,
                            activebackground=Palette.BORDER_SOFT, activeforeground=Palette.CYAN)
        help_menu.add_command(label="ℹ  À propos de Byron", command=self._show_about)
        menubar.add_cascade(label="Aide", menu=help_menu)
        
        self.root.config(menu=menubar)

    def _build_layout(self):
        self._build_header()
        body = tk.Frame(self.root, bg=Palette.BG)
        body.pack(fill="both", expand=True, padx=16, pady=(12, 0))
        body.columnconfigure(0, weight=5, minsize=420)
        body.columnconfigure(1, weight=6)
        body.rowconfigure(0, weight=1)
        
        self._build_settings_panel(body)
        self._build_console_panel(body)
        self._build_actionbar()

    def _build_header(self):
        header = tk.Frame(self.root, bg=Palette.BG_HEADER_B, height=84)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        strip = tk.Canvas(header, height=3, bg=Palette.BG_HEADER_B, highlightthickness=0)
        strip.pack(fill="x", side="top")
        self._draw_gradient(strip, Palette.CYAN, Palette.MAGENTA)
        
        content = tk.Frame(header, bg=Palette.BG_HEADER_B)
        content.pack(fill="both", expand=True, padx=20, pady=(6, 10))
        
        left = tk.Frame(content, bg=Palette.BG_HEADER_B)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="⚡ BYRON", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(left, text="MCP & API SECURITY SCANNER · RETROWAVE EDITION", style="Tag.TLabel").pack(anchor="w")
        
        right = tk.Frame(content, bg=Palette.BG_HEADER_B)
        right.pack(side="right", fill="y")
        self.status_pill = StatusPill(right)
        self.status_pill.pack(anchor="e", pady=(4, 2))
        self.elapsed_label = tk.Label(right, text="00:00", bg=Palette.BG_HEADER_B,
                                      fg=Palette.TEXT_FAINT, font=(Fonts.MONO, 10))
        self.elapsed_label.pack(anchor="e")

    @staticmethod
    def _draw_gradient(canvas, color_a, color_b):
        def render(_event=None):
            canvas.delete("grad")
            width = max(canvas.winfo_width(), 1)
            steps = 60
            r1, g1, b1 = canvas.winfo_rgb(color_a)
            r2, g2, b2 = canvas.winfo_rgb(color_b)
            for i in range(steps):
                t = i / steps
                r = int(r1 + (r2 - r1) * t) >> 8
                g = int(g1 + (g2 - g1) * t) >> 8
                b = int(b1 + (b2 - b1) * t) >> 8
                color = f"#{r:02x}{g:02x}{b:02x}"
                x0 = int(width * i / steps)
                x1 = int(width * (i + 1) / steps)
                canvas.create_rectangle(x0, 0, x1, 4, fill=color, outline="", tags="grad")
        canvas.bind("<Configure>", render)

    def _build_settings_panel(self, parent):
        wrapper = ttk.Frame(parent, style="Panel.TFrame")
        wrapper.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        
        notebook = ttk.Notebook(wrapper)
        notebook.pack(fill="both", expand=True)
        
        tab_target = self._make_card_tab(notebook, "🎯  Cible")
        tab_auth = self._make_card_tab(notebook, "🔐  Auth")
        tab_advanced = self._make_card_tab(notebook, "🛰  Proxy & Options")
        
        self._build_target_tab(tab_target)
        self._build_auth_tab(tab_auth)
        self._build_advanced_tab(tab_advanced)
        
        cfg_bar = tk.Frame(wrapper, bg=Palette.BG_PANEL)
        cfg_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(cfg_bar, text="📂 Charger config", style="Ghost.TButton",
                   command=self.load_json_config).pack(side="left", expand=True, fill="x", padx=(0, 6))
        ttk.Button(cfg_bar, text="💾 Sauvegarder config", style="Ghost.TButton",
                   command=self.save_json_config).pack(side="left", expand=True, fill="x")

    def _make_card_tab(self, notebook, label):
        outer = tk.Frame(notebook, bg=Palette.BG_CARD)
        notebook.add(outer, text=label)
        card = tk.Frame(outer, bg=Palette.BG_CARD)
        card.pack(fill="both", expand=True)
        return card

    def _build_target_tab(self, parent):
        self._section_label(parent, "Cible & protocole")
        self._entry(parent, "Target URL", "--target",
                    hint="URL de base de l'API ou du serveur MCP à auditer.",
                    placeholder="https://api.exemple.com")
        self._combobox(parent, "Type d'API", "--api-type", self.API_TYPES,
                       hint="mossbauer = scan de serveur MCP (aucun fichier d'endpoints requis).")
        self._combobox(parent, "Agressivité", "--aggression", self.AGGRESSION_LEVELS,
                       default="medium",
                       hint="low = 2.0s / 3 payloads · medium = 1.0s / 5 · high = 0.5s / tous.")
        self._file_entry(parent, "Fichier d'endpoints", "--endpoints",
                         hint="Requis sauf en mode mossbauer. Un chemin par ligne.")
        self._checkbox(parent, "Activer les tests Taurus (suite étendue)", "--taurus")

    def _build_auth_tab(self, parent):
        self._section_label(parent, "Authentification")
        self._entry(parent, "Bearer Token", "--auth-token",
                    hint="Utilisé en priorité s'il est renseigné.")
        self._section_label(parent, "— ou identifiants —", subtle=True)
        self._entry(parent, "Nom d'utilisateur", "--username")
        self._entry(parent, "Mot de passe", "--password", show="•")

    def _build_advanced_tab(self, parent):
        self._section_label(parent, "Proxy réseau")
        self._entry(parent, "Hôte proxy", "--proxy-host", default="192.168.1.20",
                    hint="Ex. Burp Suite / mitmproxy en local.")
        self._entry(parent, "Port proxy", "--proxy-port", default="8118")
        self._checkbox(parent, "Mode --noproxy (Scan direct sans proxy)", "--noproxy",
                       hint="Désactive le proxy pour frapper la cible en direct (recommandé pour Proteus-Lab en local).")
        
        self._section_label(parent, "Options d'attaque avancées")
        self._checkbox(parent, "Chaîne d'exploitation Mémétique (Protocole Dashem44)", "--memetic-chain",
                       hint="Active les tests de chaînes d'exploitation avancées (SQLi -> JWT -> IDOR -> Prompt Poisoning).")

    def _section_label(self, parent, text, subtle=False):
        style = "Hint.TLabel" if subtle else "CardTitle.TLabel"
        ttk.Label(parent, text=text, style=style).pack(anchor="w", padx=16, pady=(16, 4))

    def _entry(self, parent, label, key, default="", show=None, hint=None, placeholder=None):
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", padx=16, pady=(6, 0))
        var = tk.StringVar(value=default)
        self.vars[key] = var
        entry = ttk.Entry(parent, textvariable=var, show=show)
        entry.pack(fill="x", padx=16, pady=(2, 0))
        if placeholder and not default:
            self._apply_placeholder(entry, var, placeholder)
        if hint:
            ttk.Label(parent, text=hint, style="Hint.TLabel", wraplength=320).pack(anchor="w", padx=16, pady=(2, 2))
        self.field_errors[key] = entry
        return entry

    @staticmethod
    def _apply_placeholder(entry, var, placeholder):
        entry.insert(0, placeholder)
        entry.configure(foreground=Palette.TEXT_FAINT)
        state = {"placeholder": True}

        def on_focus_in(_e):
            if state["placeholder"]:
                entry.delete(0, tk.END)
                entry.configure(foreground=Palette.TEXT)
                state["placeholder"] = False

        def on_focus_out(_e):
            if not var.get():
                state["placeholder"] = True
                entry.insert(0, placeholder)
                entry.configure(foreground=Palette.TEXT_FAINT)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)
        original_get = var.get
        var.get = lambda: "" if state["placeholder"] else original_get()

    def _combobox(self, parent, label, key, values, default=None, hint=None):
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", padx=16, pady=(6, 0))
        var = tk.StringVar(value=default or values[0])
        self.vars[key] = var
        box = ttk.Combobox(parent, textvariable=var, values=values, state="readonly")
        box.pack(fill="x", padx=16, pady=(2, 0))
        if hint:
            ttk.Label(parent, text=hint, style="Hint.TLabel", wraplength=320).pack(anchor="w", padx=16, pady=(2, 2))
        return box

    def _file_entry(self, parent, label, key, hint=None):
        ttk.Label(parent, text=label, style="Field.TLabel").pack(anchor="w", padx=16, pady=(6, 0))
        var = tk.StringVar()
        self.vars[key] = var
        frame = tk.Frame(parent, bg=Palette.BG_CARD)
        frame.pack(fill="x", padx=16, pady=(2, 0))
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side="left", fill="x", expand=True)
        ttk.Button(frame, text="📁", width=3, style="Ghost.TButton",
                   command=lambda: var.set(filedialog.askopenfilename(
                       filetypes=[("Texte / JSON", "*.txt *.json"), ("Tous les fichiers", "*.*")]
                   ) or var.get())).pack(side="left", padx=(6, 0))
        if hint:
            ttk.Label(parent, text=hint, style="Hint.TLabel", wraplength=320).pack(anchor="w", padx=16, pady=(2, 2))
        self.field_errors[key] = entry
        return entry

    def _checkbox(self, parent, label, key, hint=None):
        var = tk.BooleanVar(value=False)
        self.vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).pack(anchor="w", padx=16, pady=(16, 4))
        if hint:
            ttk.Label(parent, text=hint, style="Hint.TLabel", wraplength=320).pack(anchor="w", padx=16, pady=(0, 4))

    def _build_console_panel(self, parent):
        card = tk.Frame(parent, bg=Palette.BG_CARD, highlightthickness=1, highlightbackground=Palette.BORDER_SOFT)
        card.grid(row=0, column=1, sticky="nsew")
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)
        
        toolbar = tk.Frame(card, bg=Palette.BG_CARD)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        ttk.Label(toolbar, text="▶ SYSTEM LOG", style="CardTitle.TLabel").pack(side="left")
        
        right_tools = tk.Frame(toolbar, bg=Palette.BG_CARD)
        right_tools.pack(side="right")
        ttk.Checkbutton(right_tools, text="Auto-scroll", variable=self.autoscroll).pack(side="left", padx=(0, 10))
        ttk.Button(right_tools, text="🧹", width=3, style="Ghost.TButton", command=self.clear_log).pack(side="left", padx=2)
        ttk.Button(right_tools, text="📋", width=3, style="Ghost.TButton", command=self.copy_log).pack(side="left", padx=2)
        
        Tooltip(right_tools.winfo_children()[-1], "Copier la console")
        Tooltip(right_tools.winfo_children()[-2], "Vider la console")
        
        self.log_text = scrolledtext.ScrolledText(
            card, bg=Palette.BG_INPUT, fg=Palette.TEXT,
            insertbackground=Palette.MAGENTA, font=(Fonts.MONO, 10),
            relief="flat", padx=10, pady=8, wrap="word", borderwidth=0,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 8))
        
        for tag, color in (
            ("debug", Palette.TEXT_FAINT), ("info", Palette.CYAN),
            ("warn", Palette.YELLOW), ("error", Palette.RED),
            ("mcp", Palette.MAGENTA), ("system", Palette.PURPLE),
        ):
            self.log_text.tag_config(tag, foreground=color)
            
        self.progress = ttk.Progressbar(card, mode="indeterminate", style="Progress.Horizontal.TProgressbar")
        self._progress_grid_opts = dict(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        
        self._append_log("[SYSTEM] Byron prêt. Configurez une cible puis lancez le scan.", "system")

    def _build_actionbar(self):
        bar = tk.Frame(self.root, bg=Palette.BG, height=64)
        bar.pack(fill="x", padx=16, pady=12)
        self.btn_start = ttk.Button(bar, text="▶  INITIALIZE SCAN", style="Primary.TButton", command=self.start_scan)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=2)
        self.btn_stop = ttk.Button(bar, text="⏹  ABORT SCAN", style="Danger.TButton", command=self.stop_scan, state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, ipady=2)
        self.root.bind("<Return>", lambda _e: self.start_scan())

    def _show_about(self):
        messagebox.showinfo(
            "À propos de Byron",
            "⚡ Byron — MCP & API Security Scanner\n"
            "Interface graphique RetroWave pour l'audit d'APIs REST/GraphQL "
            "et de serveurs MCP.\n\n"
            "À utiliser uniquement dans un cadre autorisé."
        )

    def _setup_logging_capture(self):
        self.log_handler = TkinterLogHandler(self.log_queue)
        self.log_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("[%(asctime)s] %(levelname)-7s | %(message)s", datefmt="%H:%M:%S")
        self.log_handler.setFormatter(formatter)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.DEBUG)

    def _poll_log_queue(self):
        while not self.log_queue.empty():
            msg, level = self.log_queue.get_nowait()
            self._append_log(msg, self._classify(msg, level))
        self.root.after(100, self._poll_log_queue)

    @staticmethod
    def _classify(msg, level):
        if "MOSSBAUER" in msg or "MCP" in msg.upper() or "DASHEM44" in msg or "MEMETIC" in msg.upper():
            return "mcp"
        if level >= logging.ERROR:
            return "error"
        if level >= logging.WARNING:
            return "warn"
        if level <= logging.DEBUG:
            return "debug"
        return "info"

    def _append_log(self, msg, tag="info"):
        self.log_text.insert(tk.END, msg + "\n", tag)
        if self.autoscroll.get():
            self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)
        self._append_log("[SYSTEM] Console vidée.", "system")

    def copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get("1.0", tk.END))
        self._append_log("[SYSTEM] Console copiée dans le presse-papiers.", "system")

    def export_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".log",
                                            filetypes=[("Fichier log", "*.log"), ("Texte", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.log_text.get("1.0", tk.END))
        self._append_log(f"[SYSTEM] Console exportée vers {path}", "system")

    def _tick_elapsed(self):
        if self.scan_start_time is not None:
            elapsed = int(time.time() - self.scan_start_time)
            mins, secs = divmod(elapsed, 60)
            self.elapsed_label.config(text=f"{mins:02d}:{secs:02d}", fg=Palette.CYAN)
        self.root.after(500, self._tick_elapsed)

    def load_json_config(self):
        path = filedialog.askopenfilename(filetypes=[("Config JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            for k, v in cfg.items():
                if k in self.vars:
                    self.vars[k].set(v)
            self._append_log(f"[SYSTEM] Configuration chargée depuis {path}", "system")
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Format invalide :\n{e}")

    def save_json_config(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("Config JSON", "*.json")])
        if not path:
            return
        try:
            cfg = {k: v.get() for k, v in self.vars.items()}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            self._append_log(f"[SYSTEM] Configuration sauvegardée vers {path}", "system")
        except Exception as e:
            messagebox.showerror("Erreur JSON", f"Impossible d'enregistrer :\n{e}")

    def _mark_error(self, key, is_error):
        widget = self.field_errors.get(key)
        if widget is not None:
            widget.configure(style="Error.TEntry" if is_error else "TEntry")

    def _validate(self, target, api_type, endpoints):
        ok = True
        self._mark_error("--target", False)
        self._mark_error("--endpoints", False)
        if not target:
            self._mark_error("--target", True)
            messagebox.showwarning("Validation", "Veuillez renseigner une Target URL.")
            ok = False
        elif api_type != "mossbauer":
            if not endpoints:
                self._mark_error("--endpoints", True)
                messagebox.showwarning("Validation", "Un fichier d'endpoints est requis hors mode mossbauer.")
                ok = False
            elif not os.path.exists(endpoints):
                self._mark_error("--endpoints", True)
                messagebox.showwarning("Validation", "Le fichier d'endpoints est introuvable.")
                ok = False
        return ok

    def start_scan(self):
        if self.scan_thread and self.scan_thread.is_alive():
            return
        
        target = self.vars["--target"].get().strip()
        api_type = self.vars["--api-type"].get()
        endpoints = self.vars["--endpoints"].get().strip()
        
        if not self._validate(target, api_type, endpoints):
            return
            
        config = {
            "target_url": target,
            "api_type": api_type,
            "endpoints_file": endpoints,
            "aggression_level": self.vars["--aggression"].get(),
            "taurus_enabled": self.vars["--taurus"].get(),
            "proxy_host": self.vars["--proxy-host"].get(),
            "proxy_port": self.vars["--proxy-port"].get(),
            "auth_token": self.vars["--auth-token"].get(),
            "username": self.vars["--username"].get(),
            "password": self.vars["--password"].get(),
            "noproxy": self.vars["--noproxy"].get(),              # <-- NOUVEAU
            "memetic_chain": self.vars["--memetic-chain"].get()    # <-- NOUVEAU
        }
        
        self.stop_event.clear()
        self.scan_thread = threading.Thread(target=self._run_scan_worker, args=(config,), daemon=True)
        self.scan_thread.start()
        self.scan_start_time = time.time()
        
        self.status_pill.set_state("scanning")
        self.progress.grid(**self._progress_grid_opts)
        self.progress.start(12)
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        mode_str = "DIRECT" if config["noproxy"] else "PROXY"
        chain_str = " + MEMETIC-CHAIN" if config["memetic_chain"] else ""
        self._append_log(f"[SYSTEM] ▶ Scan initialisé sur {target} ({api_type} / {config['aggression_level']} / {mode_str}{chain_str})", "system")

    def _run_scan_worker(self, config):
        try:
            tester = SecurityTester(config)
            tester.run_tests()
        except Exception as e:
            logging.error(f"CRASH: {e}")
            self.root.after(0, lambda: self.status_pill.set_state("error"))
        finally:
            self.root.after(0, self._on_scan_complete)

    def stop_scan(self):
        if messagebox.askyesno("Abandonner", "Forcer l'arrêt du scan ?\n"
                               "(des requêtes en cours peuvent ne pas être interrompues)"):
            self.stop_event.set()
            self._append_log("[SYSTEM] ⏹ Arrêt demandé par l'utilisateur…", "system")
            self.status_pill.set_state("aborted")
            self._on_scan_complete(aborted=True)

    def _on_scan_complete(self, aborted=False):
        self.progress.stop()
        self.progress.grid_forget()
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.scan_start_time = None
        if not aborted:
            self.status_pill.set_state("done")
        self._append_log("[SYSTEM] ✅ Scan terminé." if not aborted else "[SYSTEM] Scan interrompu.", "system")

# ═════════════════════════════════════════════════════════════
# LANCEMENT
# ═════════════════════════════════════════════════════════════
if __name__ == "__main__":
    root = tk.Tk()
    app = ByronApp(root)
    root.mainloop()
