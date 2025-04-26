import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from pathlib import Path


class GameSelector(tk.Frame):
    def __init__(self, master, on_game_selected):
        super().__init__(master)
        self.master = master
        self.on_game_selected = on_game_selected  # Callback per gestire la selezione del gioco

        # Configurazioni iniziali
        self.base_dir = Path(__file__).resolve().parent.parent.parent  # Directory principale del progetto
        self.game_data = {
            "onepiece": {
                "id": 15,
                "name": "One Piece",
                "icon": self.base_dir / "assets/images/onepiece_icon.png",
                "enabled": True
            },
            "pokemon": {
                "id": 5,
                "name": "Pokémon",
                "icon": self.base_dir / "assets/images/pokemon_icon.png",
                "enabled": False
            },
            "magic": {
                "id": 1,
                "name": "Magic",
                "icon": self.base_dir / "assets/images/magic_icon.png",
                "enabled": False
            }
        }

        self.create_game_buttons()

    def create_game_buttons(self):
        """Crea i pulsanti per selezionare i giochi"""
        for col, (game_key, game_data) in enumerate(self.game_data.items()):
            self.create_game_button(game_key, game_data, col)

    def create_game_button(self, game_key, game_data, column):
        """Crea un pulsante per un gioco specifico"""
        # Carica e ridimensiona l'immagine
        img = Image.open(game_data["icon"])
        img = img.resize((300, 150), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        if game_data["enabled"]:
            # Pulsante attivo per giochi abilitati
            btn = ttk.Button(
                self,
                image=photo,
                text=game_data["name"],
                compound=tk.TOP,
                command=lambda: self.on_game_selected(game_key)
            )
        else:
            # Pulsante disabilitato per giochi non abilitati
            btn = ttk.Button(
                self,
                image=photo,
                text=f"{game_data['name']}\n(Coming Soon)",
                compound=tk.TOP,
                state="disabled"
            )

        btn.image = photo  # Mantieni un riferimento all'immagine
        btn.grid(row=0, column=column, padx=20)
