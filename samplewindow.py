import customtkinter as ctk
app = ctk.CTk()
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")
app.title("Campus Event Management System")
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()
app.geometry(f"{screen_width}x{screen_height}+0+0")
# Header frame
# Top frame (header)
frame_top = ctk.CTkFrame(app, height=100, corner_radius=10)
frame_top.pack(fill="x", padx=10, pady=5)

# Sidebar frame with bottom padding
frame_left = ctk.CTkFrame(app, width=350, corner_radius=10)
frame_left.pack(side="left", fill="y", padx=10, pady=(0, 20))  # <-- bottom padding 20

# Main frame with bottom padding
frame_main = ctk.CTkFrame(app, corner_radius=10)
frame_main.pack(expand=True, fill="both", padx=0, pady=(0, 20))  # <-- bottom padding 20
# Add widgets inside frames
ctk.CTkLabel(frame_top, text="HEADER", font=("Arial", 18)).pack(pady=20,)
ctk.CTkButton(frame_left, text="Menu 1").pack(pady=10, padx=10)
ctk.CTkLabel(frame_main, text="Main Content Area").pack(pady=20)
app.mainloop()
