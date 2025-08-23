import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

import sqlite3
def on_card_click(event, event_name):
    messagebox.showinfo("Event Clicked", f"You clicked on {event_name}")
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
event_list = [
    {"name": "UI/UX Design Seminar", "date": "8/24/2025", "location": "Arts & Sciences Hall"},
    {"name": "React for Beginners Workshop", "date": "8/28/2025", "location": "Room 404, Tech Building"},
    {"name": "Annual Tech Summit 2024", "date": "9/11/2025", "location": "Main Auditorium"}
]
for event in event_list:
    frame = ctk.CTkFrame(frame_main,git padx=10, pady=10)
    frame.pack(padx=10, pady=5, fill='x')
        # Event name
    event_name = ctk.Label(frame_main, text=event['name'], font=('Arial', 14, 'bold'))
    event_name.pack(side=ctk.TOP, anchor='w')
    
    # Event details
    event_details = ctk.Label(frame_main, text=f"Date: {event['date']}\nLocation: {event['location']}")
    event_details.pack(side=ctk.TOP, anchor='w')
    
    # Bind click event
    frame.bind("<Button-1>", lambda e, name=event['name']: on_card_click(e, name))
# Add widgets inside frames
ctk.CTkLabel(frame_top, text="HEADER", font=("Arial", 18)).pack(pady=20,)
ctk.CTkButton(frame_left, text="Menu 1").pack(pady=10, padx=10)
ctk.CTkLabel(frame_main, text="Main Content Area").pack(pady=20)
app.mainloop()
