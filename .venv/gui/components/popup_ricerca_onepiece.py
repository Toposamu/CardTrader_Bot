import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import threading
import requests
import io
import webbrowser
from data.onepiece.state_manager import get_token

class RicercaPopup(tk.Toplevel):
    def __init__(self, master, totale_carte):
        super().__init__(master)
        self.title(f"Ricerca in corso 0/{totale_carte} Carte analizzate")
        self.geometry("900x600")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.master = master
        self.totale_carte = totale_carte
        self.carte_analizzate = 0

        def aggiorna_titolo(self):
            self.title(f"Ricerca in corso {self.carte_analizzate}/{self.totale_carte} Carte analizzate")

        # Area scrollabile
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.frame = tk.Frame(self.canvas)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mousewheel)  # Linux (scroll up)
        self.canvas.bind("<Button-5>", self.on_mousewheel)  # Linux (scroll down)

        self.card_widgets = []

        # Blocca la main window
        self.master.attributes("-disabled", True)

    def on_mousewheel(self, event):
        # Gestione diversa tra Windows e Linux
        if event.num == 4 or event.num == 5:
            # Linux
            delta = 1 if event.num == 5 else -1
        else:
            # Windows
            delta = 1 if event.delta < 0 else -1

        self.canvas.yview_scroll(delta, "units")
        # Questo evita che l'evento si propaghi alla finestra principale
        return "break"

    def aggiorna_titolo(self):
        self.title("Ricerca in corso {}/{} Carte analizzate".format(self.carte_analizzate, self.totale_carte))

    def aggiungi_carta(self, card_info):
        # Verifica che card_info non sia None prima di procedere
        if card_info is None:
            return
        # Verifica che card_info non sia None e non sia solo per aggiornamento
        if card_info is None or card_info.get("update_only"):
            return

        row = tk.Frame(self.frame, borderwidth=2, relief="groove", padx=4, pady=4)
        row.pack(fill="x", pady=2, padx=2)

        # Miniatura cliccabile
        try:
            response = requests.get(card_info['img_url'], timeout=10)
            img = Image.open(io.BytesIO(response.content)).resize((80, 110))
            photo = ImageTk.PhotoImage(img)
        except Exception:
            photo = None

        img_label = tk.Label(row, image=photo, cursor="hand2")
        img_label.image = photo  # evita garbage collection
        img_label.pack(side="left", padx=5)
        img_label.bind("<Button-1>", lambda e, url=card_info['url']: webbrowser.open(url))

        # Info testo
        info = tk.Frame(row)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=f"{card_info['nome']}", font=("Arial", 14, "bold")).pack(anchor="w")
        tk.Label(info, text=f"P1: {card_info['p1']}€   P2: {card_info['p2']}€", font=("Arial", 12)).pack(anchor="w")
        tk.Label(info, text=f"Convenienza: {card_info['diff_pct']}%   ({card_info['diff_abs']}€)", font=("Arial", 12, "italic")).pack(anchor="w")

        # Pulsante aggiungi al carrello
        btn = tk.Button(
            row,
            text="Aggiungi al carrello",
            bg="SystemButtonFace",
            fg="black"
        )
        btn.config(command=lambda: self.aggiungi_al_carrello(card_info['product_id'], btn))
        btn.pack(side="right", padx=10)

    def aggiungi_al_carrello(self, product_id, button):
        try:
            token = get_token()
            url = "https://api.cardtrader.com/api/v2/cart/add"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            data = {
                "product_id": product_id,
                "quantity": 1,
                "via_cardtrader_zero": True
            }
            button.config(state=tk.DISABLED, text="Aggiungendo...")
            resp = requests.post(url, headers=headers, json=data, timeout=10)
            if resp.status_code == 200:
                button.config(text="✓ Aggiunto", bg="green", fg="white", state=tk.DISABLED)
            else:
                button.config(text="❌ Errore", bg="red", fg="white", state=tk.NORMAL)
        except Exception as e:
            button.config(text="❌ Errore", bg="red", fg="white", state=tk.NORMAL)

    def aggiorna_progresso(self, analizzate):
        self.carte_analizzate = analizzate
        self.aggiorna_titolo()



    def on_close(self):
        # Rendi di nuovo la main window attiva
        self.master.attributes("-disabled", False)
        self.destroy()
