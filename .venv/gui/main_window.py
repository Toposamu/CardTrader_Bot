import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import json
from pathlib import Path
import sys
from gui.components.game_selector import GameSelector
from data.onepiece.state_manager import save_state, load_state
from data.onepiece.expansion_manager import save_excluded_expansions, load_excluded_expansions
from core.update_expansion_list import update as update_expansion_list
from data.onepiece.state_manager import get_token
from tkinter import messagebox
from data.onepiece.expansion_blueprint_generator import check_and_update_cards
from core.onepiece_search_logic import search_opportunities
from gui.components.popup_ricerca_onepiece import RicercaPopup
from tqdm import tqdm
import threading



root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CardTrader Bot")
        self.geometry("1100x700")

        # Aggiungi la variabile di stato per il filtro Zero
        self.only_zero_enabled = tk.BooleanVar(value=False)

        # Carica le immagini per il pulsante Zero
        self.zero_off_img = None
        self.zero_on_img = None

        # Configurazioni iniziali
        self.base_dir = Path(__file__).resolve().parent.parent
        self.current_game = None

        # Configura la chiusura del programma
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Mostra la schermata di selezione del gioco
        self.show_game_selector()


    def load_zero_images(self):
        """Carica le immagini per il pulsante Zero"""
        try:
            zero_off_path = self.base_dir / "assets" / "images" / "cardzero_off.png"
            zero_on_path = self.base_dir / "assets" / "images" / "cardzero_on.png"

            zero_off = Image.open(zero_off_path)
            zero_on = Image.open(zero_on_path)

            self.zero_off_img = ImageTk.PhotoImage(zero_off)
            self.zero_on_img = ImageTk.PhotoImage(zero_on)
        except Exception as e:
            print(f"❌ Errore nel caricamento delle immagini CardTrader Zero: {str(e)}")
            # Usa etichette di testo come fallback se le immagini non sono disponibili
            self.zero_off_img = None
            self.zero_on_img = None

    def toggle_zero_filter(self):
        """Alterna il filtro CardTrader Zero"""
        current_state = self.only_zero_enabled.get()
        self.only_zero_enabled.set(not current_state)

        # Aggiorna l'immagine del pulsante
        if self.only_zero_enabled.get():
            self.zero_button.config(image=self.zero_on_img)
        else:
            self.zero_button.config(image=self.zero_off_img)

    def check_expansions(self):
        """Esegue il controllo degli aggiornamenti"""
        try:
            token = get_token()
            local_file = self.base_dir / f"data/{self.current_game}/expansions.json"

            new_expansions, timestamp = update_expansion_list(
                game_id=15,  # ID di One Piece
                local_file=local_file,
                jwt_token=token
            )
            # Aggiorna lo stato visivo
            status_text = f"Ultimo controllo: {timestamp}" if timestamp else "Errore nel controllo"
            self.status_label.config(text=status_text)

            # Mostra popup se ci sono nuove espansioni
            if new_expansions:
                popup = tk.Toplevel(self)
                popup.title("Nuove Espansioni")
                ttk.Label(popup, text="Sono state aggiunte:").pack()
                for exp in new_expansions:
                    ttk.Label(popup, text=f"{exp['code']} - {exp['name']}").pack()
                ttk.Button(popup, text="OK", command=popup.destroy).pack()

                # Ricarica le espansioni e aggiorna la ListBox
                self.expansion_data = self.load_expansions(self.current_game)
                self.refresh_expansion_list()

        except Exception as e:
            print(f"❌ Errore durante il controllo: {str(e)}")
            self.status_label.config(text="Errore nel controllo")

    def update_cards(self):
        def run_update():
            try:
                exp_path = self.base_dir / f"data/{self.current_game}/expansions.json"
                with open(exp_path) as f:
                    expansions = json.load(f)

                num_expansions = len(expansions)
                self.progress_var.set(0)
                self.progress_bar["maximum"] = num_expansions

                total_report = {  # MODIFICA: Report cumulativo
                    "total_expansions": num_expansions,
                    "updated_expansions": 0,
                    "new_cards": 0,
                    "updated_cards": 0,
                    "details": {}
                }

                for i, exp in enumerate(expansions, 1):
                    # MODIFICA: Acquisisci report parziale per ogni espansione
                    partial_report = check_and_update_cards(exp["code"])

                    # Aggiorna report totale
                    total_report["updated_expansions"] += partial_report["updated_expansions"]
                    total_report["new_cards"] += partial_report["new_cards"]
                    total_report["updated_cards"] += partial_report["updated_cards"]
                    total_report["details"].update(partial_report["details"])

                    self.progress_var.set(i)
                    self.after(0, self.progress_bar.update_idletasks)

                self.after(0, lambda: self.show_update_report(total_report))

            except Exception as e:
                print(f"❌ Errore durante l'aggiornamento: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Errore", f"Errore durante l'aggiornamento: {str(e)}"))
            finally:
                self.after(0, self.progress_bar_stop)

        self.progress_bar_start()
        threading.Thread(target=run_update, daemon=True).start()

    def progress_bar_start(self):
        self.progress_bar.grid()
        self.progress_bar["value"] = 0

    def progress_bar_stop(self):
        self.progress_bar.grid_remove()

    def show_update_report(self, report):
        """Mostra un popup con il report dell'aggiornamento"""
        popup = tk.Toplevel(self)
        popup.title("Report Aggiornamento Carte")

        ttk.Label(popup, text="Report Aggiornamento Carte", font=("Arial", 14, "bold")).pack(padx=20, pady=10)

        ttk.Label(popup,
                  text=f"Espansioni aggiornate: {report['updated_expansions']}/{report['total_expansions']}").pack(
            pady=5)
        ttk.Label(popup, text=f"Nuove carte aggiunte: {report['new_cards']}").pack(pady=5)
        ttk.Label(popup, text=f"Carte aggiornate: {report['updated_cards']}").pack(pady=5)

        for exp_code, details in report["details"].items():
            frame = ttk.Frame(popup)
            frame.pack(fill="x", padx=20, pady=5)

            ttk.Label(frame, text=f"Espansione {exp_code}:").pack(anchor="w")
            if "action" in details and details["action"] == "created":
                ttk.Label(frame, text=f"• Creato nuovo file con {details['new_cards']} carte").pack(anchor="w")
            else:
                ttk.Label(frame, text=f"• Nuove carte: {details['new_cards']}").pack(anchor="w")
                ttk.Label(frame, text=f"• Carte aggiornate: {details['updated_cards']}").pack(anchor="w")

        ttk.Button(popup, text="Chiudi", command=popup.destroy).pack(pady=10)


    def show_game_selector(self):
        """Mostra la schermata di selezione del gioco"""
        self.selector_frame = GameSelector(self, self.on_game_selected)
        self.selector_frame.pack(expand=True)

    def on_game_selected(self, game_key):
        """Gestisce la selezione di un gioco"""
        print(f"Gioco selezionato: {game_key}")
        self.selector_frame.destroy()
        self.current_game = game_key
        self.show_main_interface()

    def load_game_properties(self, game_name):
        """Carica le proprietà specifiche del gioco"""
        try:
            prop_path = self.base_dir / f"data/{game_name}/{game_name}_card_properties.json"
            with open(prop_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Errore nel caricamento delle proprietà: {str(e)}")
            return {}

    def load_expansions(self, game_name):
        """Carica le espansioni specifiche del gioco"""
        try:
            exp_path = self.base_dir / f"data/{game_name}/expansions.json"
            with open(exp_path) as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Errore nel caricamento delle espansioni: {str(e)}")
            return []

    def show_main_interface(self):
        """Carica l'interfaccia principale con i parametri di ricerca"""
        properties = self.load_game_properties(self.current_game)
        expansions = self.load_expansions(self.current_game)

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # --- Filtri prezzo e differenza ---
        self.price_filter_frame = ttk.LabelFrame(self.main_frame, text="Filtri Prezzo e Convenienza")
        self.price_filter_frame.grid(row=1, column=3, sticky="ne", padx=10, pady=10)

        self.min_price_var = tk.DoubleVar(value=1.0)
        self.max_price_var = tk.DoubleVar(value=1000.0)
        self.min_diff_var = tk.DoubleVar(value=1.0)

        ttk.Label(self.price_filter_frame, text="Prezzo Min (€):").pack(anchor="w")
        ttk.Entry(self.price_filter_frame, textvariable=self.min_price_var, width=10).pack(anchor="w", pady=(0, 5))

        ttk.Label(self.price_filter_frame, text="Prezzo Max (€):").pack(anchor="w")
        ttk.Entry(self.price_filter_frame, textvariable=self.max_price_var, width=10).pack(anchor="w", pady=(0, 5))

        ttk.Label(self.price_filter_frame, text="Diff. Min (€):").pack(anchor="w")
        ttk.Entry(self.price_filter_frame, textvariable=self.min_diff_var, width=10).pack(anchor="w", pady=(0, 5))

        # Aggiungi il pulsante CardTrader Zero dopo i filtri prezzo
        self.load_zero_images()
        self.zero_button_frame = ttk.Frame(self.price_filter_frame)
        self.zero_button_frame.pack(anchor="w", pady=(10, 5))

        ttk.Label(self.zero_button_frame, text="Solo carte CardTrader Zero:").pack(anchor="w")
        self.zero_button = tk.Button(
            self.zero_button_frame,
            image=self.zero_off_img,
            command=self.toggle_zero_filter,
            borderwidth=0,
            highlightthickness=0,
            relief="flat"
        )
        self.zero_button.pack(anchor="w", pady=(5, 5))

        # Logo del gioco sopra le colonne
        logo_frame = ttk.Frame(self.main_frame)
        logo_frame.grid(row=0, column=0, columnspan=3, pady=10)

        logo_path = self.base_dir / f"assets/images/{self.current_game}_icon.png"
        logo_img = Image.open(logo_path).resize((150, 75), Image.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)

        logo_label = ttk.Label(logo_frame, image=logo_photo)
        logo_label.image = logo_photo
        logo_label.pack()

        # Colonne dinamiche
        self.create_filter_column("Lingua", properties.get(f"{self.current_game}_language", []), 0, 20)
        self.create_filter_column("Rarità", properties.get(f"{self.current_game}_rarity", []), 1, 20)
        self.create_expansion_column(expansions, 2, 40)

        # Pulsante Avvia Ricerca in alto a destra
        top_right_frame = ttk.Frame(self.main_frame)
        top_right_frame.grid(row=0, column=3, sticky="ne", padx=10, pady=10)

        big_button = tk.Button(
            top_right_frame,
            text="AVVIA RICERCA",
            font=("Arial", 16),
            bg="red",
            fg="white",
            height=2,
            width=20,
            command=self.start_search
        )
        big_button.pack()

        # Pulsante "Indietro" in basso a sinistra
        bottom_left_frame = ttk.Frame(self.main_frame)
        bottom_left_frame.grid(row=2, column=0, sticky="sw", padx=10, pady=10)
        ttk.Button(bottom_left_frame, text="Indietro", command=self.return_to_selector).pack(anchor="w")

        # Aggiungi status label in basso a destra
        self.status_label = ttk.Label(self.main_frame)
        self.status_label.grid(row=2, column=3, sticky="se", padx=10, pady=10)

        # Pulsante "Aggiorna Carte" in basso a destra
        bottom_right_frame = ttk.Frame(self.main_frame)
        bottom_right_frame.grid(row=2, column=2, sticky="se", padx=10, pady=10)
        ttk.Button(bottom_right_frame, text="Aggiorna Carte", command=self.update_cards).pack(anchor="e")

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            self.main_frame,
            orient="horizontal",
            length=400,
            mode="determinate",
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=4, column=0, columnspan=4, pady=(10, 0))
        self.progress_bar.grid_remove()

        # Esegui il controllo automatico
        self.check_expansions()



    def create_filter_column(self, title, items, column, width):
        """Crea una colonna di filtri con checkboxes"""
        frame = ttk.LabelFrame(self.main_frame, text=title, labelanchor="n")
        frame.grid(row=1, column=column, sticky=tk.NSEW, padx=10, pady=10)

        saved_state = load_state()
        selected_items = saved_state["languages"] if title == "Lingua" else saved_state["rarities"]

        checkboxes = []
        for i, item in enumerate(items):
            initial_value = 1 if item in selected_items else 0
            var = tk.IntVar(value=initial_value)
            cb = tk.Checkbutton(frame, text=item, variable=var)
            cb.grid(row=i, column=0, sticky=tk.W)
            checkboxes.append({"text": item, "variable": var})

        if title == "Lingua":
            self.language_checkboxes = checkboxes
        elif title == "Rarità":
            self.rarity_checkboxes = checkboxes

    def create_expansion_column(self, expansions, column, width):
        """Crea la colonna per la selezione delle espansioni"""
        frame = ttk.LabelFrame(self.main_frame, text="Espansioni", labelanchor="n")
        frame.grid(row=1, column=column, sticky=tk.NSEW, padx=10, pady=10)

        self.expansion_data = expansions  # Salva i dati originali
        self.excluded_expansions = load_excluded_expansions()  # Carica esclusioni salvate

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.expansion_listbox = tk.Listbox(
            frame,
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set,
            height=20,
            width=int(width),
            font=("Arial", 14)
        )
        self.expansion_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.expansion_listbox.yview)

        # Popola la lista
        self.refresh_expansion_list()

        # Bind per il tasto destro
        self.expansion_listbox.bind("<Button-3>", self.show_context_menu)

    # gui/main_window.py (aggiungi questi metodi alla classe)
    def toggle_exclusion(self, code, exclude):
        """Gestisce l'esclusione o il ripristino di un'espansione"""
        if exclude:
            if code not in self.excluded_expansions:
                self.excluded_expansions.append(code)
        else:
            if code in self.excluded_expansions:
                self.excluded_expansions.remove(code)

        # Salva le esclusioni e aggiorna la lista
        save_excluded_expansions(self.excluded_expansions)
        self.refresh_expansion_list()

    def refresh_expansion_list(self):
        """Aggiorna la lista delle espansioni visualizzate"""
        self.expansion_listbox.delete(0, tk.END)

        # Espansioni normali
        for exp in self.expansion_data:
            if exp["code"] not in self.excluded_expansions:
                self.expansion_listbox.insert(tk.END, f"{exp['code']} - {exp['name']}")

        # Espansioni escluse (in grigio)
        for exp in self.expansion_data:
            if exp["code"] in self.excluded_expansions:
                index = self.expansion_listbox.size()
                self.expansion_listbox.insert(tk.END, f"{exp['code']} - {exp['name']} (esclusa)")
                self.expansion_listbox.itemconfig(index, fg="gray")

    def show_context_menu(self, event):
        """Mostra il menu contestuale per escludere/ripristinare"""
        index = self.expansion_listbox.nearest(event.y)
        text = self.expansion_listbox.get(index)
        code = text.split(" - ")[0]

        menu = tk.Menu(self, tearoff=0)

        if "(esclusa)" in text:
            menu.add_command(label="Ripristina", command=lambda: self.toggle_exclusion(code, False))
        else:
            menu.add_command(label="Escludi", command=lambda: self.toggle_exclusion(code, True))

        menu.tk_popup(event.x_root, event.y_root)

    def save_current_state(self):
        """Salva lo stato attuale delle selezioni."""
        languages = [cb["text"] for cb in self.language_checkboxes if cb["variable"].get() == 1]
        rarities = [cb["text"] for cb in self.rarity_checkboxes if cb["variable"].get() == 1]
        save_state(languages, rarities)

    def on_close(self):
        """Gestisce la chiusura del programma."""
        self.save_current_state()
        self.destroy()

    def select_all_expansions(self):
        """Seleziona tutte le espansioni nella listbox"""
        self.expansion_listbox.select_set(0, tk.END)

    def deselect_all_expansions(self):
        """Deseleziona tutte le espansioni nella listbox"""
        self.expansion_listbox.select_clear(0, tk.END)

    def get_selected_expansions(self):
        """Restituisce gli ID delle espansioni selezionate"""
        selected_indices = self.expansion_listbox.curselection()
        displayed_expansions = []

        # Ricostruisci la lista come nella logica precedente
        for exp in self.expansion_data:
            if exp["code"] not in self.excluded_expansions:
                displayed_expansions.append(exp)
        for exp in self.expansion_data:
            if exp["code"] in self.excluded_expansions:
                displayed_expansions.append(exp)

        # Mappa codice→ID
        expansions_file = self.base_dir / "data" / "onepiece" / "expansions.json"
        with open(expansions_file) as f:
            all_expansions = json.load(f)
        expansion_map = {exp["code"]: exp["id"] for exp in all_expansions}

        return [
            expansion_map[displayed_expansions[i]["code"]]
            for i in selected_indices
            if i < len(displayed_expansions)
        ]

    def get_selected_languages(self):
        """Restituisce le lingue selezionate"""
        return [
            cb["text"].lower()
            for cb in self.language_checkboxes
            if cb["variable"].get() == 1
        ]

    def get_selected_rarities(self):
        """Restituisce le rarità selezionate"""
        return [
            cb["text"]
            for cb in self.rarity_checkboxes
            if cb["variable"].get() == 1
        ]

    def start_search(self):
        try:
            # 1. Calcola il numero totale di carte da analizzare
            selected_indices = self.expansion_listbox.curselection()
            displayed_expansions = []

            # Ricostruisci la lista delle espansioni visualizzate
            for exp in self.expansion_data:
                if exp["code"] not in self.excluded_expansions:
                    displayed_expansions.append(exp)
            for exp in self.expansion_data:
                if exp["code"] in self.excluded_expansions:
                    displayed_expansions.append(exp)

            # 2. Calcola quante carte totali saranno analizzate
            total_cards = 0
            for i in selected_indices:
                if i >= len(displayed_expansions):
                    continue

                exp_code = displayed_expansions[i]["code"]
                exp_file = self.base_dir / "data" / "onepiece" / "blueprints" / f"{exp_code}.json"

                if not exp_file.exists():
                    continue

                try:
                    with open(exp_file, "r", encoding="utf-8") as f:
                        cards = json.load(f)
                        total_cards += len(cards)
                except Exception as e:
                    print(f"❌ Errore lettura file {exp_code}: {str(e)}")

            # 3. Crea il popup con il totale calcolato
            self.popup_ricerca = RicercaPopup(self, total_cards)

            # 4. Recupera i parametri di ricerca
            min_price = self.min_price_var.get()
            max_price = self.max_price_var.get()
            min_diff = self.min_diff_var.get()
            only_zero = self.only_zero_enabled.get()

            # 5. Avvia la ricerca in un thread separato
            threading.Thread(
                target=self.esegui_ricerca_con_popup,
                args=(
                    self.get_selected_expansions(),
                    self.get_selected_languages(),
                    self.get_selected_rarities(),
                    min_price,
                    max_price,
                    min_diff,
                    only_zero,
                    self.popup_ricerca
                ),
                daemon=True
            ).start()

        except Exception as e:
            print(f"❌ Errore durante l'avvio della ricerca: {str(e)}")
            messagebox.showerror("Errore", f"Errore durante l'avvio:\n{str(e)}")

    def esegui_ricerca_con_popup(self, expansions, languages, rarities, min_price, max_price, min_diff, only_zero, popup):
        from core.onepiece_search_logic import search_opportunities_popup

        print("\n⚙️ PARAMETRI DI RICERCA:")
        print(f"- Espansioni selezionate: {expansions}")
        print(f"- Lingue selezionate: {languages}")
        print(f"- Rarità selezionate: {rarities}")
        print(f"- Prezzo minimo: {min_price}€")
        print(f"- Prezzo massimo: {max_price}€")
        print(f"- Differenza minima: {min_diff}€")
        print(f"- Solo carte CardTrader Zero: {only_zero}")
        print("\n🔍 Avvio ricerca...")

        def on_carta_trovata(card_info, analizzate):
            self.after(0, lambda: popup.aggiorna_progresso(analizzate))
            self.after(0, lambda: popup.aggiungi_carta(card_info))

        search_opportunities_popup(
            expansions, languages, rarities,
            min_price, max_price, min_diff,
            only_zero, on_carta_trovata
        )



    def return_to_selector(self):
        """Torna alla schermata di selezione del gioco"""
        self.main_frame.destroy()  # Distrugge la schermata principale
        self.show_game_selector()  # Richiama la schermata di selezione del gioco


if __name__ == "__main__":
    app = MainApplication()
    app.mainloop()
