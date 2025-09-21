# gui.py

import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import threading
import os
import time
from pathlib import Path
from main import run_processing_for_list
from config import path_config
from queue import Queue, Empty
import fitz

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Likumu Datu Apstrādes Rīks v3.1")
        self.geometry("1200x800")  # Slightly larger for better usability
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        
        # Initialize directories
        if not path_config.setup_directories():
            messagebox.showerror("Kļūda", "Neizdevās izveidot nepieciešamās mapes!")
            self.destroy()
            return

        # Top frame for file selection
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)

        self.label_path = ctk.CTkLabel(self.frame_top, text="Nav izvēlēts fails vai mape", wraplength=400)
        self.label_path.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.button_select_file = ctk.CTkButton(self.frame_top, text="📄 Izvēlēties PDF", command=self.select_file)
        self.button_select_file.grid(row=0, column=0, padx=(20, 10), pady=10)

        self.button_select_folder = ctk.CTkButton(self.frame_top, text="📁 Izvēlēties Mapi", command=self.select_folder)
        self.button_select_folder.grid(row=0, column=2, padx=(10, 20), pady=10)

        # Status frame
        self.frame_status = ctk.CTkFrame(self)
        self.frame_status.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.frame_status.grid_columnconfigure(0, weight=1)

        self.label_status = ctk.CTkLabel(self.frame_status, text="Gatavs apstrādei", fg_color="transparent")
        self.label_status.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # Main text area
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 11), wrap="word")
        self.log_textbox.grid(row=2, column=0, padx=20, pady=5, sticky="nsew")
        
        # Configure text tags for better formatting
        self.log_textbox.tag_config('meta', foreground='#666666')
        self.log_textbox.tag_config('title', justify='center', foreground='#0066cc')
        self.log_textbox.tag_config('article', foreground='#003366', spacing1=8)
        self.log_textbox.tag_config('point', lmargin1=30, lmargin2=30, foreground='#006600')
        self.log_textbox.tag_config('subpoint', lmargin1=60, lmargin2=60, foreground='#0066cc')
        self.log_textbox.tag_config('content', lmargin1=30, lmargin2=30, foreground='#333333')
        self.log_textbox.tag_config('error', foreground='#cc0000')

        # Bottom control frame
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.frame_bottom.grid_columnconfigure(0, weight=1)
        self.frame_bottom.grid_columnconfigure(1, weight=0)

        self.button_start = ctk.CTkButton(
            self.frame_bottom, 
            text="▶️ Sākt Apstrādi", 
            command=self.start_processing_thread, 
            state="disabled",
            height=40
        )
        self.button_start.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        # Checkbox for pdfplumber fallback
        self.var_plumber = ctk.BooleanVar(value=path_config.use_pdfplumber_fallback)
        self.checkbox_plumber = ctk.CTkCheckBox(
            self.frame_bottom,
            text="Pdfplumber Fallback",
            variable=self.var_plumber,
            onvalue=True,
            offvalue=False,
            command=self.toggle_plumber,
        )
        self.checkbox_plumber.grid(row=0, column=1, padx=(0, 20), pady=10)

        # Progress frame
        self.frame_progress = ctk.CTkFrame(self.frame_bottom)
        self.frame_progress.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.frame_progress.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(self.frame_progress)
        self.progressbar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.progressbar.set(0)

        self.label_progress = ctk.CTkLabel(self.frame_progress, text="", fg_color="transparent")
        self.label_progress.grid(row=1, column=0, padx=10, pady=(0, 10))

        # Initialize variables
        self.selected_paths = []
        self.log_queue = Queue()
        self.total_pages = 0
        self.pages_processed = 0
        self.is_processing = False
        self.start_time = None

        # Initial welcome message
        self.show_welcome_message()

    def show_welcome_message(self):
        """Display welcome message with instructions."""
        welcome_text = """🎯 LIKUMU DATU APSTRĀDES RĪKS v3.1

📖 INSTRUKCIJAS:
1. Izvēlieties PDF failu vai mapi ar vairākiem PDF failiem
2. Nospiediet "Sākt Apstrādi" pogu
3. Vērojiet apstrādes procesu šajā logā

📁 REZULTĀTI:
• JSON faili: processed_json/
• Apstrādātie PDF: processed_pdfs/
• Kļūdainie faili: error_pdfs/

⚙️ IESTATĪJUMI:
• Maksimālais faila izmērs: {max_size}MB
• Apstrādes timeout: {timeout}s

Izvēlieties failus, lai sāktu...
""".format(max_size=path_config.max_file_size_mb, timeout=path_config.processing_timeout)
        
        self.clear_and_log(welcome_text, 'meta')

    def select_file(self):
        """Select single PDF file with validation."""
        try:
            filepath = filedialog.askopenfilename(
                title="Izvēlieties PDF failu",
                filetypes=[("PDF faili", "*.pdf"), ("Visi faili", "*")]
            )
            if filepath:
                file_path = Path(filepath)
                is_valid, error_msg = path_config.validate_file(file_path)
                
                if not is_valid:
                    messagebox.showerror("Faila kļūda", f"Nevar apstrādāt failu:\n{error_msg}")
                    return
                
                self.selected_paths = [file_path]
                self.label_path.configure(text=f"📄 {file_path.name}")
                self.button_start.configure(state="normal")
                self.update_status(f"Atlasīts 1 fails: {file_path.name}")
                self.clear_and_log(f"✅ Atlasīts fails: {filepath}\n", 'meta')
                
        except Exception as e:
            messagebox.showerror("Kļūda", f"Kļūda faila izvēlē: {e}")

    def select_folder(self):
        """Select folder with PDF validation."""
        try:
            folderpath = filedialog.askdirectory(title="Izvēlieties mapi ar PDF failiem")
            if folderpath:
                folder = Path(folderpath)
                all_pdfs = list(folder.glob("*.pdf"))
                
                if not all_pdfs:
                    messagebox.showwarning("Nav failu", "Atlasītajā mapē netika atrasti PDF faili.")
                    return
                
                # Validate files
                valid_files = []
                invalid_files = []
                
                for pdf_file in all_pdfs:
                    is_valid, error_msg = path_config.validate_file(pdf_file)
                    if is_valid:
                        valid_files.append(pdf_file)
                    else:
                        invalid_files.append((pdf_file.name, error_msg))
                
                if not valid_files:
                    messagebox.showerror("Nav derīgu failu", "Neviens fails mapē nav derīgs apstrādei.")
                    return
                
                self.selected_paths = valid_files
                self.label_path.configure(text=f"📁 {folderpath}")
                self.button_start.configure(state="normal")
                
                status_msg = f"Atlasīti {len(valid_files)} derīgi faili no {len(all_pdfs)}"
                self.update_status(status_msg)
                
                log_msg = f"✅ Atlasīta mape: {folderpath}\n✓ Derīgi faili: {len(valid_files)}\n"
                if invalid_files:
                    log_msg += f"⚠️ Nederīgi faili ({len(invalid_files)}):\n"
                    for name, reason in invalid_files[:5]:  # Show first 5
                        log_msg += f"  • {name}: {reason}\n"
                    if len(invalid_files) > 5:
                        log_msg += f"  • ... un vēl {len(invalid_files) - 5}\n"
                
                self.clear_and_log(log_msg, 'meta')
                
        except Exception as e:
            messagebox.showerror("Kļūda", f"Kļūda mapes izvēlē: {e}")

    def toggle_plumber(self):
        """Toggle pdfplumber fallback feature flag"""
        path_config.use_pdfplumber_fallback = self.var_plumber.get()

    def update_status(self, message: str, is_error: bool = False):
        """Update status label."""
        self.label_status.configure(text=message)
        if is_error:
            self.label_status.configure(text_color="red")
        else:
            self.label_status.configure(text_color=("gray10", "gray90"))

    def log_message(self, message, tag='meta'):
        """Add message to log with proper formatting."""
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", message, (tag,))
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
            self.update_idletasks()
        except Exception:
            pass  # Ignore errors during shutdown

    def clear_and_log(self, message, tag='meta'):
        """Clear log and add new message."""
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.delete("1.0", "end")
            self.log_textbox.insert("1.0", message, (tag,))
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def process_log_queue(self):
        """Process messages from processing thread."""
        if not self.is_processing:
            return
            
        try:
            processed_count = 0
            while processed_count < 100 and not self.log_queue.empty():
                try:
                    message, tag = self.log_queue.get_nowait()
                    
                    if tag == "progress_update":
                        self.pages_processed += 1
                        if self.total_pages > 0:
                            progress = min(self.pages_processed / self.total_pages, 1.0)
                            self.progressbar.set(progress)
                            
                            # Update progress label
                            if self.start_time:
                                elapsed = time.time() - self.start_time
                                if progress > 0:
                                    eta = (elapsed / progress) * (1 - progress)
                                    self.label_progress.configure(
                                        text=f"Progress: {self.pages_processed}/{self.total_pages} lpp. "
                                             f"({progress*100:.1f}%) • ETA: {eta:.0f}s"
                                    )
                    else:
                        self.log_message(message, tag)
                    
                    processed_count += 1
                    
                except Empty:
                    break
                    
        except Exception:
            pass  # Ignore errors during shutdown
        finally:
            if self.is_processing:
                self.after(30, self.process_log_queue)  # Faster updates

    def calculate_total_pages(self) -> int:
        """Calculate total pages in all selected files."""
        total = 0
        failed_files = []
        
        for pdf_path in self.selected_paths:
            try:
                with fitz.open(pdf_path) as doc:
                    total += doc.page_count
            except Exception as e:
                failed_files.append((pdf_path.name, str(e)))
        
        if failed_files:
            self.log_message(f"⚠️ Neizdevās nolasīt {len(failed_files)} failus:\n", 'error')
            for name, error in failed_files[:3]:
                self.log_message(f"  • {name}: {error}\n", 'error')
        
        return total

    def start_processing_thread(self):
        """Start processing in background thread."""
        try:
            # Disable controls
            self.button_start.configure(state="disabled", text="⏳ Apstrādā...")
            self.button_select_file.configure(state="disabled")
            self.button_select_folder.configure(state="disabled")
            self.is_processing = True
            self.start_time = time.time()
            
            # Calculate total pages
            self.update_status("Aprēķina kopējo lapu skaitu...")
            self.clear_and_log("🔍 Aprēķina kopējo lapu skaitu...\n", 'meta')
            
            self.pages_processed = 0
            self.total_pages = self.calculate_total_pages()
            
            if self.total_pages == 0:
                self.update_status("Kļūda: Nav derīgu failu apstrādei", True)
                self.reset_ui()
                return
            
            self.log_message(f"📊 Kopā apstrādei: {self.total_pages} lapas\n", 'meta')
            self.log_message(f"📁 Failu skaits: {len(self.selected_paths)}\n\n", 'meta')
            self.update_status(f"Apstrādā {len(self.selected_paths)} failus...")
            
            self.progressbar.set(0)
            self.label_progress.configure(text="Sāk apstrādi...")
            
            # Start processing thread
            processing_thread = threading.Thread(target=self.processing_worker, daemon=True)
            processing_thread.start()
            
            # Start log queue processing
            self.process_log_queue()
            
        except Exception as e:
            messagebox.showerror("Kļūda", f"Neizdevās sākt apstrādi: {e}")
            self.reset_ui()

    def reset_ui(self):
        """Reset UI to initial state."""
        self.is_processing = False
        self.button_start.configure(state="normal", text="▶️ Sākt Apstrādi")
        self.button_select_file.configure(state="normal")
        self.button_select_folder.configure(state="normal")
        self.progressbar.set(0)
        self.label_progress.configure(text="")
        self.update_status("Gatavs apstrādei")

    def processing_worker(self):
        """Background processing worker."""
        try:
            # Run the actual processing
            run_processing_for_list(self.selected_paths, self.log_queue)
            
            # Processing completed
            processing_time = time.time() - self.start_time if self.start_time else 0
            self.log_queue.put((f"\n🎉 APSTRĀDE PABEIGTA!\n", 'meta'))
            self.log_queue.put((f"⏱️  Kopējais laiks: {processing_time:.1f} sekundes\n", 'meta'))
            self.log_queue.put((f"📊 Apstrādātas {self.pages_processed} lapas\n", 'meta'))
            
            # Schedule UI updates
            self.after(100, lambda: [
                self.progressbar.set(1),
                self.label_progress.configure(text="✅ Pabeigts!"),
                self.update_status("Apstrāde pabeigta veiksmīgi"),
                self.log_textbox.configure(state="normal")  # Allow scrolling
            ])
            
            self.after(1000, self.reset_ui)  # Reset after 1 second
            
        except Exception as e:
            self.log_queue.put((f"\n❌ KRITISKA KĻŪDA: {e}\n", 'error'))
            self.after(100, lambda: [
                self.update_status("Apstrādes kļūda", True),
                self.log_textbox.configure(state="normal")
            ])
            self.after(2000, self.reset_ui)

if __name__ == "__main__":
    app = App()
    app.mainloop()