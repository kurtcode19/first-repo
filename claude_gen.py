import customtkinter as ctk
import sqlite3
import pandas as pd
import tkinter.messagebox as msgbox
import tkinter.filedialog as filedialog
from tkinter import ttk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import json

# Set appearance mode and default color theme
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

class DatabaseManager:
    def __init__(self, db_name="campus_events.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                description TEXT,
                event_date TEXT NOT NULL,
                location TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                department TEXT NOT NULL,
                year_level INTEGER NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Registrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                registration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER,
                student_id TEXT,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attendance_status BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (event_id) REFERENCES events (event_id),
                FOREIGN KEY (student_id) REFERENCES students (student_id),
                UNIQUE(event_id, student_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a query and return results"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                results = cursor.fetchall()
                conn.close()
                return results
            else:
                conn.commit()
                conn.close()
                return cursor.rowcount
        except sqlite3.Error as e:
            conn.close()
            raise e

class EventManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_event(self, name, description, date, location):
        """Add a new event"""
        query = """
            INSERT INTO events (event_name, description, event_date, location)
            VALUES (?, ?, ?, ?)
        """
        return self.db.execute_query(query, (name, description, date, location))
    
    def get_all_events(self):
        """Get all events"""
        query = "SELECT * FROM events ORDER BY event_date DESC"
        return self.db.execute_query(query)
    
    def update_event(self, event_id, name, description, date, location):
        """Update an event"""
        query = """
            UPDATE events 
            SET event_name = ?, description = ?, event_date = ?, location = ?
            WHERE event_id = ?
        """
        return self.db.execute_query(query, (name, description, date, location, event_id))
    
    def delete_event(self, event_id):
        """Delete an event"""
        # First delete registrations
        self.db.execute_query("DELETE FROM registrations WHERE event_id = ?", (event_id,))
        # Then delete the event
        return self.db.execute_query("DELETE FROM events WHERE event_id = ?", (event_id,))

class StudentManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def add_student(self, student_id, first_name, last_name, department, year_level, email=""):
        """Add a new student"""
        query = """
            INSERT INTO students (student_id, first_name, last_name, department, year_level, email)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.db.execute_query(query, (student_id, first_name, last_name, department, year_level, email))
    
    def get_student(self, student_id):
        """Get student by ID"""
        query = "SELECT * FROM students WHERE student_id = ?"
        results = self.db.execute_query(query, (student_id,))
        return results[0] if results else None
    
    def get_all_students(self):
        """Get all students"""
        query = "SELECT * FROM students ORDER BY last_name, first_name"
        return self.db.execute_query(query)
    
    def import_students_from_excel(self, file_path):
        """Import students from Excel file"""
        try:
            df = pd.read_excel(file_path)
            
            # Expected columns: student_id, first_name, last_name, department, year_level, email
            required_columns = ['student_id', 'first_name', 'last_name', 'department', 'year_level']
            
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"Excel file must contain columns: {', '.join(required_columns)}")
            
            imported_count = 0
            for _, row in df.iterrows():
                try:
                    self.add_student(
                        str(row['student_id']),
                        str(row['first_name']),
                        str(row['last_name']),
                        str(row['department']),
                        int(row['year_level']),
                        str(row.get('email', ''))
                    )
                    imported_count += 1
                except sqlite3.IntegrityError:
                    # Student already exists, skip
                    continue
            
            return imported_count
        except Exception as e:
            raise e

class RegistrationManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def register_student(self, event_id, student_id):
        """Register a student for an event"""
        query = """
            INSERT INTO registrations (event_id, student_id)
            VALUES (?, ?)
        """
        return self.db.execute_query(query, (event_id, student_id))
    
    def mark_attendance(self, event_id, student_id):
        """Mark student attendance for an event"""
        query = """
            UPDATE registrations 
            SET attendance_status = TRUE 
            WHERE event_id = ? AND student_id = ?
        """
        return self.db.execute_query(query, (event_id, student_id))
    
    def get_event_registrations(self, event_id):
        """Get all registrations for an event"""
        query = """
            SELECT r.*, s.first_name, s.last_name, s.department, s.year_level
            FROM registrations r
            JOIN students s ON r.student_id = s.student_id
            WHERE r.event_id = ?
        """
        return self.db.execute_query(query, (event_id,))

class ReportsManager:
    def __init__(self, db_manager):
        self.db = db_manager
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        # Total events
        total_events = self.db.execute_query("SELECT COUNT(*) FROM events")[0][0]
        
        # Total students
        total_students = self.db.execute_query("SELECT COUNT(*) FROM students")[0][0]
        
        # Total registrations
        total_registrations = self.db.execute_query("SELECT COUNT(*) FROM registrations")[0][0]
        
        return {
            'total_events': total_events,
            'total_students': total_students,
            'total_registrations': total_registrations
        }
    
    def get_upcoming_events(self):
        """Get upcoming events"""
        query = """
            SELECT e.*, COUNT(r.registration_id) as registered_count
            FROM events e
            LEFT JOIN registrations r ON e.event_id = r.event_id
            WHERE date(e.event_date) >= date('now')
            GROUP BY e.event_id
            ORDER BY e.event_date ASC
            LIMIT 10
        """
        return self.db.execute_query(query)
    
    def get_event_attendance_stats(self):
        """Get attendance statistics for all events"""
        query = """
            SELECT e.event_name, 
                   COUNT(r.registration_id) as total_registered,
                   SUM(CASE WHEN r.attendance_status = 1 THEN 1 ELSE 0 END) as total_attended
            FROM events e
            LEFT JOIN registrations r ON e.event_id = r.event_id
            GROUP BY e.event_id, e.event_name
        """
        return self.db.execute_query(query)
    
    def get_department_participation(self):
        """Get participation statistics by department"""
        query = """
            SELECT s.department, COUNT(r.registration_id) as registrations
            FROM students s
            JOIN registrations r ON s.student_id = r.student_id
            GROUP BY s.department
        """
        return self.db.execute_query(query)

class ModernCampusEventApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Offline School Event Management")
        self.root.geometry("1400x900")
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.event_manager = EventManager(self.db_manager)
        self.student_manager = StudentManager(self.db_manager)
        self.registration_manager = RegistrationManager(self.db_manager)
        self.reports_manager = ReportsManager(self.db_manager)
        
        # Current active view
        self.current_view = "Dashboard"
        
        self.setup_ui()
        self.show_dashboard()
    
    def setup_ui(self):
        """Setup the main user interface with sidebar layout"""
        # Configure grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.main_frame = ctk.CTkFrame(self.root, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create scrollable frame for main content
        self.content_frame = ctk.CTkScrollableFrame(self.main_frame)
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
    
    def create_sidebar(self):
        """Create the sidebar navigation"""
        self.sidebar = ctk.CTkFrame(self.root, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)
        
        # App title
        app_title = ctk.CTkLabel(
            self.sidebar, 
            text="Event Manager",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white"
        )
        app_title.grid(row=0, column=0, padx=20, pady=(30, 40))
        
        # Navigation buttons
        self.nav_buttons = {}
        nav_items = [
            ("📊", "Dashboard"),
            ("📅", "Events"), 
            ("📈", "Reports")
        ]
        
        for i, (icon, name) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=f"{icon}  {name}",
                font=ctk.CTkFont(size=14),
                height=40,
                width=160,
                anchor="w",
                command=lambda n=name: self.switch_view(n)
            )
            btn.grid(row=i, column=0, padx=20, pady=5)
            self.nav_buttons[name] = btn
        
        # Footer
        footer_label = ctk.CTkLabel(
            self.sidebar,
            text="© 2025 School Admin\nOffline Version",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        footer_label.grid(row=11, column=0, padx=20, pady=20)
    
    def switch_view(self, view_name):
        """Switch between different views"""
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Update button states
        for name, btn in self.nav_buttons.items():
            if name == view_name:
                btn.configure(fg_color=("#3B82F6", "#1E40AF"))
            else:
                btn.configure(fg_color=("#1F2937", "#374151"))
        
        self.current_view = view_name
        
        # Show appropriate view
        if view_name == "Dashboard":
            self.show_dashboard()
        elif view_name == "Events":
            self.show_events()
        elif view_name == "Reports":
            self.show_reports()
    
    def show_dashboard(self):
        """Show the dashboard view"""
        # Page title
        title = ctk.CTkLabel(
            self.content_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w"
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 30))
        
        # Get dashboard stats
        stats = self.reports_manager.get_dashboard_stats()
        
        # Stats cards
        stats_frame = ctk.CTkFrame(self.content_frame)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 30))
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Total Events card
        self.create_stat_card(stats_frame, "📅", "Total Events", stats['total_events'], 0, 0)
        
        # Total Students card  
        self.create_stat_card(stats_frame, "👥", "Total Students", stats['total_students'], 0, 1)
        
        # Total Registrations card
        self.create_stat_card(stats_frame, "📝", "Total Registrations", stats['total_registrations'], 0, 2)
        
        # Upcoming Events section
        upcoming_title = ctk.CTkLabel(
            self.content_frame,
            text="Upcoming Events",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w"
        )
        upcoming_title.grid(row=2, column=0, sticky="w", pady=(0, 20))
        
        # Upcoming events cards
        self.show_upcoming_events()
    
    def create_stat_card(self, parent, icon, title, value, row, col):
        """Create a statistics card"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="ew")
        
        # Icon and value
        icon_label = ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=24))
        icon_label.pack(pady=(20, 5))
        
        value_label = ctk.CTkLabel(card, text=str(value), font=ctk.CTkFont(size=24, weight="bold"))
        value_label.pack()
        
        title_label = ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="gray")
        title_label.pack(pady=(5, 20))
    
    def show_upcoming_events(self):
        """Show upcoming events in card format"""
        upcoming_events = self.reports_manager.get_upcoming_events()
        
        if not upcoming_events:
            no_events_label = ctk.CTkLabel(
                self.content_frame,
                text="No upcoming events found.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_events_label.grid(row=3, column=0, pady=20)
            return
        
        events_container = ctk.CTkFrame(self.content_frame)
        events_container.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        
        for i, event in enumerate(upcoming_events[:3]):  # Show max 3 events
            self.create_event_card(events_container, event, i)
    
    def create_event_card(self, parent, event, row):
        """Create an event card"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=0, sticky="ew", padx=10, pady=10)
        card.grid_columnconfigure(0, weight=1)
        
        # Event name
        name_label = ctk.CTkLabel(
            card,
            text=event[1],  # event_name
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        # Event details
        details_frame = ctk.CTkFrame(card, fg_color="transparent")
        details_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))
        details_frame.grid_columnconfigure(2, weight=1)
        
        # Date
        date_label = ctk.CTkLabel(details_frame, text=f"🗓 {event[3]}", font=ctk.CTkFont(size=12))
        date_label.grid(row=0, column=0, sticky="w")
        
        # Location
        location_label = ctk.CTkLabel(details_frame, text=f"📍 {event[4]}", font=ctk.CTkFont(size=12))
        location_label.grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        # Registration count
        reg_count = event[6] if len(event) > 6 else 0
        reg_label = ctk.CTkLabel(details_frame, text=f"{reg_count} registered", 
                                font=ctk.CTkFont(size=12), text_color="gray")
        reg_label.grid(row=0, column=2, sticky="e")
    
    def show_events(self):
        """Show the events management view"""
        # Page title and create button
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title = ctk.CTkLabel(
            header_frame,
            text="Events",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w"
        )
        title.grid(row=0, column=0, sticky="w")
        
        create_btn = ctk.CTkButton(
            header_frame,
            text="+ Create Event",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=35,
            command=self.show_create_event_dialog
        )
        create_btn.grid(row=0, column=1, sticky="e")
        
        # Search and filter
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        search_frame.grid_columnconfigure(0, weight=1)
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search events by name or venue...",
            height=35,
            font=ctk.CTkFont(size=14)
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        filter_label = ctk.CTkLabel(search_frame, text="Filter:")
        filter_label.grid(row=0, column=1, padx=(10, 5))
        
        self.filter_combo = ctk.CTkComboBox(
            search_frame,
            values=["All", "Upcoming", "Past"],
            width=120,
            height=35
        )
        self.filter_combo.grid(row=0, column=2)
        self.filter_combo.set("All")
        
        # Events grid
        self.show_events_grid()
    
    def show_events_grid(self):
        """Show events in a card grid layout"""
        # Clear previous events if any
        if hasattr(self, 'events_container'):
            self.events_container.destroy()
        
        events = self.event_manager.get_all_events()
        
        if not events:
            no_events_label = ctk.CTkLabel(
                self.content_frame,
                text="No events found. Create your first event!",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_events_label.grid(row=2, column=0, pady=50)
            return
        
        self.events_container = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.events_container.grid(row=2, column=0, sticky="ew")
        self.events_container.grid_columnconfigure((0, 1, 2), weight=1)
        
        for i, event in enumerate(events):
            row = i // 3
            col = i % 3
            self.create_detailed_event_card(self.events_container, event, row, col)
    
    def create_detailed_event_card(self, parent, event, row, col):
        """Create a detailed event card with actions"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="new")
        
        # Status badge
        status = "Upcoming" if event[3] >= str(datetime.now().date()) else "Past"
        status_color = "#10B981" if status == "Upcoming" else "#6B7280"
        
        status_badge = ctk.CTkLabel(
            card,
            text=status,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="white",
            fg_color=status_color,
            corner_radius=10,
            width=70,
            height=20
        )
        status_badge.grid(row=0, column=1, sticky="e", padx=15, pady=(15, 5))
        
        # Event name
        name_label = ctk.CTkLabel(
            card,
            text=event[1][:30] + "..." if len(event[1]) > 30 else event[1],
            font=ctk.CTkFont(size=16, weight="bold"),
            anchor="w"
        )
        name_label.grid(row=1, column=0, columnspan=2, sticky="ew", padx=15, pady=(5, 10))
        
        # Date and location
        details_frame = ctk.CTkFrame(card, fg_color="transparent")
        details_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=15)
        
        date_label = ctk.CTkLabel(details_frame, text=f"🗓 {event[3]}", font=ctk.CTkFont(size=12))
        date_label.pack(anchor="w", pady=2)
        
        location_label = ctk.CTkLabel(details_frame, text=f"📍 {event[4]}", font=ctk.CTkFont(size=12))
        location_label.pack(anchor="w", pady=2)
        
        # Get registration count
        registrations = self.registration_manager.get_event_registrations(event[0])
        reg_count = len(registrations)
        
        reg_label = ctk.CTkLabel(details_frame, text=f"👥 {reg_count} / 50 Participants", 
                                font=ctk.CTkFont(size=12))
        reg_label.pack(anchor="w", pady=2)
        
        # Action buttons
        action_frame = ctk.CTkFrame(card, fg_color="transparent")
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=15)
        
        view_btn = ctk.CTkButton(
            action_frame,
            text="View Details",
            width=80,
            height=30,
            font=ctk.CTkFont(size=12),
            command=lambda e=event: self.view_event_details(e)
        )
        view_btn.pack(side="left")
        
        edit_btn = ctk.CTkButton(
            action_frame,
            text="✏️",
            width=30,
            height=30,
            font=ctk.CTkFont(size=12),
            command=lambda e=event: self.edit_event(e)
        )
        edit_btn.pack(side="right", padx=(5, 0))
        
        delete_btn = ctk.CTkButton(
            action_frame,
            text="🗑️",
            width=30,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="red",
            hover_color="darkred",
            command=lambda e=event: self.delete_event(e)
        )
        delete_btn.pack(side="right", padx=5)
    
    def show_create_event_dialog(self):
        """Show create event dialog"""
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Create New Event")
        dialog.geometry("400x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"400x500+{x}+{y}")
        
        # Form fields
        ctk.CTkLabel(dialog, text="Create New Event", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        # Event name
        ctk.CTkLabel(dialog, text="Event Name:", anchor="w").pack(fill="x", padx=30, pady=(10, 5))
        name_entry = ctk.CTkEntry(dialog, height=35)
        name_entry.pack(fill="x", padx=30, pady=(0, 10))
        
        # Description
        ctk.CTkLabel(dialog, text="Description:", anchor="w").pack(fill="x", padx=30, pady=(0, 5))
        desc_entry = ctk.CTkEntry(dialog, height=35)
        desc_entry.pack(fill="x", padx=30, pady=(0, 10))
        
        # Date
        ctk.CTkLabel(dialog, text="Date (YYYY-MM-DD):", anchor="w").pack(fill="x", padx=30, pady=(0, 5))
        date_entry = ctk.CTkEntry(dialog, height=35)
        date_entry.pack(fill="x", padx=30, pady=(0, 10))
        
        # Location
        ctk.CTkLabel(dialog, text="Location:", anchor="w").pack(fill="x", padx=30, pady=(0, 5))
        location_entry = ctk.CTkEntry(dialog, height=35)
        location_entry.pack(fill="x", padx=30, pady=(0, 20))
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=20)
        
        def create_event():
            name = name_entry.get().strip()
            description = desc_entry.get().strip()
            date = date_entry.get().strip()
            location = location_entry.get().strip()
            
            if not all([name, date, location]):
                msgbox.showerror("Error", "Please fill in all required fields")
                return
            
            try:
                self.event_manager.add_event(name, description, date, location)
                msgbox.showinfo("Success", "Event created successfully!")
                dialog.destroy()
                if self.current_view == "Events":
                    self.show_events_grid()
            except Exception as e:
                msgbox.showerror("Error", f"Failed to create event: {str(e)}")
        
        ctk.CTkButton(btn_frame, text="Cancel", 
                     command=dialog.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="Create Event", 
                     command=create_event).pack(side="right")
    
    def view_event_details(self, event):
        """Show detailed event view with registration functionality"""
        # Clear current content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Back button and title
        header_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header_frame.grid_columnconfigure(1, weight=1)
        
        back_btn = ctk.CTkButton(
            header_frame,
            text="← Back to Events",
            width=120,
            command=lambda: self.switch_view("Events")
        )
        back_btn.grid(row=0, column=0, sticky="w")
        
        title = ctk.CTkLabel(
            header_frame,
            text=event[1],  # Event name
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        # Event info section
        info_frame = ctk.CTkFrame(self.content_frame)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        info_frame.grid_columnconfigure(0, weight=1)
        
        # Description
        desc_label = ctk.CTkLabel(
            info_frame,
            text=event[2] if event[2] else "A hands-on workshop covering the fundamentals of React.",
            font=ctk.CTkFont(size=14),
            anchor="w"
        )
        desc_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))
        
        # Event details row
        details_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        details_row.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        details_row.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Date
        date_frame = ctk.CTkFrame(details_row, fg_color="transparent")
        date_frame.grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(date_frame, text="🗓", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(date_frame, text=f"{event[3]}, 12:18:27 PM", 
                    font=ctk.CTkFont(size=12)).pack(side="left", padx=(5, 0))
        
        # Location
        location_frame = ctk.CTkFrame(details_row, fg_color="transparent")
        location_frame.grid(row=0, column=1, sticky="w")
        
        ctk.CTkLabel(location_frame, text="📍", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(location_frame, text=event[4], 
                    font=ctk.CTkFont(size=12)).pack(side="left", padx=(5, 0))
        
        # Participants count
        registrations = self.registration_manager.get_event_registrations(event[0])
        reg_count = len(registrations)
        
        participants_frame = ctk.CTkFrame(details_row, fg_color="transparent")
        participants_frame.grid(row=0, column=2, sticky="w")
        
        ctk.CTkLabel(participants_frame, text="👥", font=ctk.CTkFont(size=16)).pack(side="left")
        ctk.CTkLabel(participants_frame, text=f"{reg_count} / 25", 
                    font=ctk.CTkFont(size=12)).pack(side="left", padx=(5, 0))
        
        # Registration section
        reg_section = ctk.CTkFrame(self.content_frame)
        reg_section.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        ctk.CTkLabel(reg_section, text="Register Student", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        reg_form = ctk.CTkFrame(reg_section, fg_color="transparent")
        reg_form.pack(fill="x", padx=20, pady=(0, 20))
        
        # Search/register input
        input_frame = ctk.CTkFrame(reg_form, fg_color="transparent")
        input_frame.pack(fill="x")
        input_frame.grid_columnconfigure(0, weight=1)
        
        student_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Search student by name or ID...",
            height=35
        )
        student_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        register_btn = ctk.CTkButton(
            input_frame,
            text="Register",
            height=35,
            width=100,
            command=lambda: self.register_student_for_event(event[0], student_entry)
        )
        register_btn.grid(row=0, column=1)
        
        # Participants & Attendance section
        participants_section = ctk.CTkFrame(self.content_frame)
        participants_section.grid(row=3, column=0, sticky="ew", fill="both", expand=True)
        
        ctk.CTkLabel(participants_section, text="Participants & Attendance", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        # Create table for participants
        if registrations:
            # Table headers
            headers_frame = ctk.CTkFrame(participants_section)
            headers_frame.pack(fill="x", padx=20, pady=(0, 10))
            headers_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            
            headers = ["STUDENT ID", "NAME", "DEPARTMENT", "ATTENDANCE", "ACTIONS"]
            for i, header in enumerate(headers):
                ctk.CTkLabel(headers_frame, text=header, 
                           font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=i, pady=10)
            
            # Scrollable frame for participant rows
            participants_scroll = ctk.CTkScrollableFrame(participants_section, height=200)
            participants_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            participants_scroll.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            
            for i, registration in enumerate(registrations):
                self.create_participant_row(participants_scroll, registration, i)
        else:
            no_participants = ctk.CTkLabel(
                participants_section,
                text="No students registered yet.",
                font=ctk.CTkFont(size=14),
                text_color="gray"
            )
            no_participants.pack(pady=50)
    
    def create_participant_row(self, parent, registration, row):
        """Create a row for participant in the table"""
        row_frame = ctk.CTkFrame(parent)
        row_frame.grid(row=row, column=0, sticky="ew", pady=2, padx=5)
        row_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        
        # Student ID
        ctk.CTkLabel(row_frame, text=registration[2]).grid(row=0, column=0, pady=10, padx=5)
        
        # Name
        full_name = f"{registration[4]} {registration[5]}"
        ctk.CTkLabel(row_frame, text=full_name).grid(row=0, column=1, pady=10, padx=5)
        
        # Department
        ctk.CTkLabel(row_frame, text=registration[6]).grid(row=0, column=2, pady=10, padx=5)
        
        # Attendance status
        attendance_text = "Present" if registration[4] else "Absent"
        attendance_color = "green" if registration[4] else "red"
        ctk.CTkLabel(row_frame, text=attendance_text, text_color=attendance_color).grid(row=0, column=3, pady=10, padx=5)
        
        # Actions
        if not registration[4]:  # If not attended yet
            attend_btn = ctk.CTkButton(
                row_frame,
                text="Mark Present",
                width=80,
                height=25,
                font=ctk.CTkFont(size=10),
                command=lambda: self.mark_student_attendance(registration[1], registration[2])
            )
            attend_btn.grid(row=0, column=4, pady=10, padx=5)
        else:
            ctk.CTkLabel(row_frame, text="✓", text_color="green", 
                        font=ctk.CTkFont(size=16)).grid(row=0, column=4, pady=10, padx=5)
    
    def register_student_for_event(self, event_id, student_entry):
        """Register a student for an event"""
        student_input = student_entry.get().strip()
        if not student_input:
            msgbox.showerror("Error", "Please enter a student ID")
            return
        
        # Check if student exists
        student = self.student_manager.get_student(student_input)
        if not student:
            msgbox.showerror("Error", "Student not found. Please add the student first.")
            return
        
        try:
            self.registration_manager.register_student(event_id, student_input)
            msgbox.showinfo("Success", f"Student {student_input} registered successfully!")
            student_entry.delete(0, 'end')
            # Refresh the current view to show updated registration
            event = self.event_manager.get_all_events()
            for e in event:
                if e[0] == event_id:
                    self.view_event_details(e)
                    break
        except sqlite3.IntegrityError:
            msgbox.showerror("Error", "Student is already registered for this event")
        except Exception as e:
            msgbox.showerror("Error", f"Failed to register student: {str(e)}")
    
    def mark_student_attendance(self, event_id, student_id):
        """Mark student attendance"""
        try:
            self.registration_manager.mark_attendance(event_id, student_id)
            msgbox.showinfo("Success", f"Attendance marked for student {student_id}")
            # Refresh view
            event = self.event_manager.get_all_events()
            for e in event:
                if e[0] == event_id:
                    self.view_event_details(e)
                    break
        except Exception as e:
            msgbox.showerror("Error", f"Failed to mark attendance: {str(e)}")
    
    def edit_event(self, event):
        """Edit an existing event"""
        msgbox.showinfo("Info", "Edit functionality will be implemented in the next version")
    
    def delete_event(self, event):
        """Delete an event"""
        if msgbox.askyesno("Confirm", f"Are you sure you want to delete '{event[1]}'?"):
            try:
                self.event_manager.delete_event(event[0])
                msgbox.showinfo("Success", "Event deleted successfully!")
                self.show_events_grid()
            except Exception as e:
                msgbox.showerror("Error", f"Failed to delete event: {str(e)}")
    
    def show_reports(self):
        """Show the reports view"""
        # Page title
        title = ctk.CTkLabel(
            self.content_frame,
            text="Reports",
            font=ctk.CTkFont(size=28, weight="bold"),
            anchor="w"
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 30))
        
        # Event selector
        selector_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        selector_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        selector_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(selector_frame, text="Select Event for Report:").grid(row=0, column=0, padx=(0, 10))
        
        events = self.event_manager.get_all_events()
        event_options = [f"{event[1]}" for event in events]
        
        if event_options:
            self.report_event_combo = ctk.CTkComboBox(
                selector_frame,
                values=event_options,
                width=300
            )
            self.report_event_combo.grid(row=0, column=1, sticky="w")
            self.report_event_combo.set(event_options[0] if event_options else "")
            
            # Show report for first event by default
            if events:
                self.show_event_report(events[0])
        else:
            ctk.CTkLabel(selector_frame, text="No events available", 
                        text_color="gray").grid(row=0, column=1, sticky="w")
    
    def show_event_report(self, event):
        """Show detailed report for a specific event"""
        # Clear previous report if exists
        if hasattr(self, 'report_container'):
            self.report_container.destroy()
        
        self.report_container = ctk.CTkFrame(self.content_frame)
        self.report_container.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        
        # Event summary header
        ctk.CTkLabel(
            self.report_container,
            text=f"Event Summary: {event[1]}",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(20, 10))
        
        # Stats cards
        stats_frame = ctk.CTkFrame(self.report_container)
        stats_frame.pack(fill="x", padx=20, pady=(0, 20))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        registrations = self.registration_manager.get_event_registrations(event[0])
        total_registered = len(registrations)
        total_present = sum(1 for r in registrations if r[4])  # attendance_status
        total_absent = total_registered - total_present
        
        # Create stats cards
        self.create_report_stat_card(stats_frame, str(total_registered), "Registered", "#3B82F6", 0)
        self.create_report_stat_card(stats_frame, str(total_present), "Present", "#10B981", 1)
        self.create_report_stat_card(stats_frame, str(total_absent), "Absent", "#EF4444", 2)
        self.create_report_stat_card(stats_frame, "0", "Late", "#F59E0B", 3)
        
        # Department Distribution (placeholder for chart)
        dept_frame = ctk.CTkFrame(self.report_container)
        dept_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(dept_frame, text="Department Distribution", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=20)
        
        # Simple text-based department stats
        if registrations:
            dept_stats = {}
            for reg in registrations:
                dept = reg[6]  # department
                dept_stats[dept] = dept_stats.get(dept, 0) + 1
            
            for dept, count in dept_stats.items():
                dept_label = ctk.CTkLabel(dept_frame, text=f"{dept}: {count} students")
                dept_label.pack(pady=2)
        else:
            ctk.CTkLabel(dept_frame, text="No data available", text_color="gray").pack(pady=20)
        
        # Participant List
        participants_frame = ctk.CTkFrame(self.report_container)
        participants_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ctk.CTkLabel(participants_frame, text="Participant List", 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 10))
        
        if registrations:
            # Headers
            headers_frame = ctk.CTkFrame(participants_frame)
            headers_frame.pack(fill="x", padx=10, pady=(0, 5))
            headers_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            
            headers = ["STUDENT ID", "NAME", "DEPARTMENT", "YEAR", "ATTENDANCE"]
            for i, header in enumerate(headers):
                ctk.CTkLabel(headers_frame, text=header, 
                           font=ctk.CTkFont(size=10, weight="bold")).grid(row=0, column=i, pady=5)
            
            # Participant data
            data_scroll = ctk.CTkScrollableFrame(participants_frame, height=150)
            data_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
            data_scroll.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
            
            for i, reg in enumerate(registrations):
                row_frame = ctk.CTkFrame(data_scroll)
                row_frame.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
                row_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
                
                ctk.CTkLabel(row_frame, text=reg[2], font=ctk.CTkFont(size=10)).grid(row=0, column=0, pady=5)
                ctk.CTkLabel(row_frame, text=f"{reg[4]} {reg[5]}", font=ctk.CTkFont(size=10)).grid(row=0, column=1, pady=5)
                ctk.CTkLabel(row_frame, text=reg[6], font=ctk.CTkFont(size=10)).grid(row=0, column=2, pady=5)
                ctk.CTkLabel(row_frame, text=str(reg[7]), font=ctk.CTkFont(size=10)).grid(row=0, column=3, pady=5)
                
                attendance = "Present" if reg[4] else "Absent"
                color = "green" if reg[4] else "red"
                ctk.CTkLabel(row_frame, text=attendance, text_color=color, 
                           font=ctk.CTkFont(size=10)).grid(row=0, column=4, pady=5)
        else:
            ctk.CTkLabel(participants_frame, text="No participants registered", 
                        text_color="gray").pack(pady=30)
    
    def create_report_stat_card(self, parent, value, label, color, col):
        """Create a stat card for reports"""
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, padx=10, pady=10, sticky="ew")
        
        # Value
        value_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color=color)
        value_label.pack(pady=(15, 5))
        
        # Label
        label_label = ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=12), text_color="gray")
        label_label.pack(pady=(0, 15))
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

# Main execution
if __name__ == "__main__":
    app = ModernCampusEventApp()
    app.run()