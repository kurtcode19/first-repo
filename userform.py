import sqlite3
import customtkinter as ctk
import tkinter as tk
def init():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL
        )
        '''
    )
    print("database created successfully!")
    conn.commit()
    conn.close()
init()
def submit():
    username = username.get()
    email = email.get()
    password = password.get()
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO users (username, email, password)
        VALUES (?, ?, ?)
        ''',
        (username, email, password)
    )
    conn.commit()
    conn.close()
app = ctk.CTk()
app.geometry("1020x1080")
app.attributes('-fullscreen',True)
app.title("User Form")
loglabel = ctk.CTkLabel(app, text="Username:")
loglabel.pack(pady=10)
username = ctk.CTkEntry(app)
username.pack(pady=10)
emaillabel = ctk.CTkLabel(app, text="Email:")
emaillabel.pack(pady=10)
email = ctk.CTkEntry(app)
email.pack(pady=10)
passwordlabel = ctk.CTkLabel(app, text="Password:")
passwordlabel.pack(pady=10)
password = ctk.CTkEntry(app, show="*")
password.pack(pady=10)
submit_button = ctk.CTkButton(app, text="Submit", command=submit)
submit_button.pack(pady=10)
app.mainloop()

