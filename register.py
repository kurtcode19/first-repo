import sqlite3
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

# ---------------------------
# Database Setup
# ---------------------------
def init_db():
    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE,
            first_name TEXT,
            last_name TEXT,
            department TEXT,
            year_level TEXT
        )
    """)
    conn.commit()
    conn.close()

# ---------------------------
# Save Student Function
# ---------------------------
def save_student():
    sid = id_entry.get()
    fname = fname_entry.get()
    lname = lname_entry.get()
    dept = dept_entry.get()
    year = year_entry.get()

    if not sid or not fname or not lname:
        messagebox.showerror("Error", "Please fill in all required fields!")
        return

    try:
        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO students (student_id, first_name, last_name, department, year_level) VALUES (?, ?, ?, ?, ?)",
                       (sid, fname, lname, dept, year))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Student registered successfully!")
        
        # Clear fields
        id_entry.delete(0, tk.END)
        fname_entry.delete(0, tk.END)
        lname_entry.delete(0, tk.END)
        dept_entry.delete(0, tk.END)
        year_entry.delete(0, tk.END)

    except sqlite3.IntegrityError:
        messagebox.showerror("Error", "Student ID already exists!")

# ---------------------------
# UI Setup
# ---------------------------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

app = ctk.CTk()
app.title("Campus Event Registration System")
app.state("zoomed")
# Menu bar (Tkinter)
menubar = tk.Menu(app)
file_menu = tk.Menu(menubar, tearoff=0)
file_menu.add_command(label="Exit", command=app.quit)
menubar.add_cascade(label="File", menu=file_menu)
app.config(menu=menubar)

# Title
title_label = ctk.CTkLabel(app, text="Student Registration", font=("Segoe UI", 20, "bold"))
title_label.pack(pady=20)

# Form Frame
frame = ctk.CTkFrame(app, corner_radius=10)
frame.pack(padx=20, pady=10, fill="both", expand=True)
label = ctk.CTkLabel(frame, text= "REGISTER FORM")
label.pack()

id_entry = ctk.CTkEntry(frame, placeholder_text="Student ID")
id_entry.pack(pady=10, padx=20, fill="x")

fname_entry = ctk.CTkEntry(frame, placeholder_text="First Name")
fname_entry.pack(pady=10, padx=20, fill="x")

lname_entry = ctk.CTkEntry(frame, placeholder_text="Last Name")
lname_entry.pack(pady=10, padx=20, fill="x")

dept_entry = ctk.CTkEntry(frame, placeholder_text="Department")
dept_entry.pack(pady=10, padx=20, fill="x")

year_entry = ctk.CTkEntry(frame, placeholder_text="Year Level")
year_entry.pack(pady=10, padx=20, fill="x")

submit_btn = ctk.CTkButton(frame, text="Register Student", width=200, height=40, corner_radius=8, command=save_student)
submit_btn.pack(pady=20)

# Status Bar (classic Tkinter)
status = tk.Label(app, text="Ready", bd=1, relief=tk.SUNKEN, anchor="w")
status.pack(side=tk.BOTTOM, fill=tk.X)

# Initialize DB
init_db()

app.mainloop()
