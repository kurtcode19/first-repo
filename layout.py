import tkinter as tk
from tkinter import messagebox

# Function to handle card click
def on_card_click(event, event_name):
    messagebox.showinfo("Event Clicked", f"You clicked on {event_name}")

# Main application window
root = tk.Tk()
root.title("Event Manager")
root.geometry("400x400")

# List of events
events = [
    {"name": "UI/UX Design Seminar", "date": "8/24/2025", "location": "Arts & Sciences Hall"},
    {"name": "React for Beginners Workshop", "date": "8/28/2025", "location": "Room 404, Tech Building"},
    {"name": "Annual Tech Summit 2024", "date": "9/11/2025", "location": "Main Auditorium"}
]

# Creating cards for each event
for event in events:
    frame = tk.Frame(root, borderwidth=1, relief="raised", padx=10, pady=10)
    frame.pack(padx=10, pady=5, fill='x')
    
    # Event name
    event_name = tk.Label(frame, text=event['name'], font=('Arial', 14, 'bold'))
    event_name.pack(side=tk.TOP, anchor='w')
    
    # Event details
    event_details = tk.Label(frame, text=f"Date: {event['date']}\nLocation: {event['location']}")
    event_details.pack(side=tk.TOP, anchor='w')
    
    # Bind click event
    frame.bind("<Button-1>", lambda e, name=event['name']: on_card_click(e, name))

# Start the application
root.mainloop()
