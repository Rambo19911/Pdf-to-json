# gui.py

import customtkinter as ctk
import tkinter.filedialog as filedialog
import threading
import os
from pathlib import Path
from main import run_processing_for_list
from queue import Queue
import fitz # Pievienojam fitz importu, lai saskaitītu lapas

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Likumu Datu Apstrādes Rīks")
        self.geometry("1000x700")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # ... (pārējais __init__ kods līdz TAGU KONFIGURĀCIJAI paliek nemainīgs) ...
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)
        self.label_path = ctk.CTkLabel(self.frame_top, text="Nav izvēlēts fails vai mape")
        self.label_path.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.button_select_file = ctk.CTkButton(self.frame_top, text="Izvēlēties PDF Failu", command=self.select_file)
        self.button_select_file.grid(row=0, column=0, padx=(20, 10), pady=10)
        self.button_select_folder = ctk.CTkButton(self.frame_top, text="Izvēlēties Mapi", command=self.select_folder)
        self.button_select_folder.grid(row=0, column=2, padx=(10, 20), pady=10)
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.frame_bottom.grid_columnconfigure(0, weight=1)
        self.button_start = ctk.CTkButton(self.frame_bottom, text="Sākt Apstrādi", command=self.start_processing_thread, state="disabled")
        self.button_start.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.progressbar = ctk.CTkProgressBar(self.frame_bottom)
        self.progressbar.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.progressbar.set(0)
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", font=("Verdana", 12), wrap="word")
        self.log_textbox.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        
        self.log_textbox.tag_config('meta', foreground='#888888')
        self.log_textbox.tag_config('title', justify='center', foreground='#0077be', spacing3=10)
        self.log_textbox.tag_config('article', foreground='#003656', spacing1=15)
        self.log_textbox.tag_config('point', lmargin1=25, lmargin2=25)
        self.log_textbox.tag_config('subpoint', lmargin1=50, lmargin2=50)
        self.log_textbox.tag_config('content', lmargin1=25, lmargin2=25)
        self.log_textbox.tag_config('error', foreground='red')

        self.selected_paths = []
        self.log_queue = Queue()
        # === JAUNI MAINĪGIE PROGRESAM ===
        self.total_pages = 0
        self.pages_processed = 0

    def select_file(self, *args, **kwargs):
        # ... (funkcija paliek nemainīga) ...
        filepath = filedialog.askopenfilename(filetypes=[("PDF faili", "*.pdf")])
        if filepath:
            self.selected_paths = [Path(filepath)]
            self.label_path.configure(text=os.path.basename(filepath))
            self.button_start.configure(state="normal")
            self.clear_and_log(f"Atlasīts fails: {filepath}\n", 'meta')

    def select_folder(self, *args, **kwargs):
        # ... (funkcija paliek nemainīga) ...
        folderpath = filedialog.askdirectory()
        if folderpath:
            folder = Path(folderpath)
            self.selected_paths = list(folder.glob("*.pdf"))
            self.label_path.configure(text=folderpath)
            self.clear_and_log(f"Atlasīta mape: {folderpath}\n", 'meta')
            if self.selected_paths:
                self.button_start.configure(state="normal")
                self.log_message(f"Atrasti {len(self.selected_paths)} PDF faili.\n", 'meta')
            else:
                self.log_message(f"BRĪDINĀJUMS: Atlasītajā mapē netika atrasti PDF faili.\n", 'error')
                self.button_start.configure(state="disabled")

    def log_message(self, message, tag='meta'):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message, (tag,))
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
        self.update_idletasks()

    def clear_and_log(self, message, tag='meta'):
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.insert("1.0", message, (tag,))
        self.log_textbox.configure(state="disabled")

    def process_log_queue(self):
        max_per_cycle = 50 
        try:
            self.log_textbox.configure(state="normal")
            for _ in range(max_per_cycle):
                if not self.log_queue.empty():
                    message, tag = self.log_queue.get_nowait()
                    
                    # === LABOJUMS PROGRESAM ===
                    if tag == "progress_update":
                        self.pages_processed += 1
                        progress = self.pages_processed / self.total_pages
                        self.progressbar.set(progress)
                    else:
                        self.log_textbox.insert("end", message, (tag,))
                else:
                    break
            self.log_textbox.configure(state="disabled")
            self.log_textbox.see("end")
        finally:
            self.after(50, self.process_log_queue)

    def start_processing_thread(self):
        self.button_start.configure(state="disabled")
        self.button_select_file.configure(state="disabled")
        self.button_select_folder.configure(state="disabled")
        self.clear_and_log("Aprēķina kopējo lapu skaitu...\n", 'meta')

        # === JAUNA LOĢIKA PROGRESAM ===
        self.pages_processed = 0
        self.total_pages = 0
        try:
            for pdf_path in self.selected_paths:
                with fitz.open(pdf_path) as doc:
                    self.total_pages += doc.page_count
        except Exception as e:
            self.log_message(f"Kļūda, nolasot PDF failu lapu skaita noteikšanai: {e}\n", "error")
            return
            
        self.log_message(f"Kopā apstrādei: {self.total_pages} lpp.\nSāk apstrādi...\n", 'meta')
        self.progressbar.set(0) # Atiestatām uz 0
        
        processing_thread = threading.Thread(target=self.processing_worker)
        processing_thread.daemon = True
        processing_thread.start()
        
        self.process_log_queue()

    def enable_scrolling(self):
        """Padara teksta logu lasāmu un ritināmu, bet ne rediģējamu."""
        self.log_textbox.configure(state="normal")
    
    def processing_worker(self):
        run_processing_for_list(self.selected_paths, self.log_queue)
        
        self.log_queue.put(("\n=== APSTRĀDE PABEIGTA ===\n", 'meta'))
        
        # === LABOJUMS RITINĀŠANAI ===
        # Pasakām UI pavedienam, ka teksta logs ir jāpadara ritināms
        self.after(100, self.enable_scrolling) 
        
        self.progressbar.set(1)
        self.button_start.configure(state="normal")
        self.button_select_file.configure(state="normal")
        self.button_select_folder.configure(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()