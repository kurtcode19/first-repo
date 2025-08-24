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
    
    def export_to_excel(self, data, headers, filename):
        """Export data to Excel file"""
        df = pd.DataFrame(data, columns=headers)
        df.to_excel(filename, index=False)

class CampusEventApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Campus Event Management System")
        self.root.geometry("1200x800")
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.event_manager = EventManager(self.db_manager)
        self.student_manager = StudentManager(self.db_manager)
        self.registration_manager = RegistrationManager(self.db_manager)
        self.reports_manager = ReportsManager(self.db_manager)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Main title
        title_label = ctk.CTkLabel(
            self.root, 
            text="Campus Event Management System",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create tabs
        self.notebook.add("Events")
        self.notebook.add("Students")
        self.notebook.add("Registration")
        self.notebook.add("Reports")
        
        self.setup_events_tab()
        self.setup_students_tab()
        self.setup_registration_tab()
        self.setup_reports_tab()
    
    def setup_events_tab(self):
        """Setup the events management tab"""
        events_frame = self.notebook.tab("Events")
        
        # Add Event Section
        add_frame = ctk.CTkFrame(events_frame)
        add_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(add_frame, text="Add New Event", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Form fields
        form_frame = ctk.CTkFrame(add_frame)
        form_frame.pack(fill="x", padx=10, pady=5)
        
        # Event Name
        ctk.CTkLabel(form_frame, text="Event Name:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.event_name_entry = ctk.CTkEntry(form_frame, width=300)
        self.event_name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Description
        ctk.CTkLabel(form_frame, text="Description:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.event_desc_entry = ctk.CTkEntry(form_frame, width=300)
        self.event_desc_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Date
        ctk.CTkLabel(form_frame, text="Date (YYYY-MM-DD):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.event_date_entry = ctk.CTkEntry(form_frame, width=300)
        self.event_date_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Location
        ctk.CTkLabel(form_frame, text="Location:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.event_location_entry = ctk.CTkEntry(form_frame, width=300)
        self.event_location_entry.grid(row=3, column=1, padx=5, pady=5)
        
        # Buttons
        button_frame = ctk.CTkFrame(add_frame)
        button_frame.pack(pady=10)
        
        ctk.CTkButton(button_frame, text="Add Event", command=self.add_event).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Refresh List", command=self.refresh_events_list).pack(side="left", padx=5)
        
        # Events List
        list_frame = ctk.CTkFrame(events_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkLabel(list_frame, text="Events List", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Create treeview for events list
        columns = ("ID", "Name", "Description", "Date", "Location")
        self.events_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.events_tree.heading(col, text=col)
            self.events_tree.column(col, width=150)
        
        self.events_tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Delete button
        ctk.CTkButton(list_frame, text="Delete Selected Event", command=self.delete_event).pack(pady=5)
        
        self.refresh_events_list()
    
    def setup_students_tab(self):
        """Setup the students management tab"""
        students_frame = self.notebook.tab("Students")
        
        # Import Students Section
        import_frame = ctk.CTkFrame(students_frame)
        import_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(import_frame, text="Import Students", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        import_button_frame = ctk.CTkFrame(import_frame)
        import_button_frame.pack(pady=10)
        
        ctk.CTkButton(import_button_frame, text="Import from Excel", command=self.import_students).pack(side="left", padx=5)
        ctk.CTkButton(import_button_frame, text="Download Sample Excel", command=self.download_sample_excel).pack(side="left", padx=5)
        
        # Add Single Student Section
        add_student_frame = ctk.CTkFrame(students_frame)
        add_student_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(add_student_frame, text="Add Single Student", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Form fields
        student_form_frame = ctk.CTkFrame(add_student_frame)
        student_form_frame.pack(fill="x", padx=10, pady=5)
        
        # Student ID
        ctk.CTkLabel(student_form_frame, text="Student ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.student_id_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # First Name
        ctk.CTkLabel(student_form_frame, text="First Name:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.student_fname_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_fname_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Last Name
        ctk.CTkLabel(student_form_frame, text="Last Name:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.student_lname_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_lname_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Department
        ctk.CTkLabel(student_form_frame, text="Department:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.student_dept_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_dept_entry.grid(row=1, column=3, padx=5, pady=5)
        
        # Year Level
        ctk.CTkLabel(student_form_frame, text="Year Level:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.student_year_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_year_entry.grid(row=2, column=1, padx=5, pady=5)
        
        # Email
        ctk.CTkLabel(student_form_frame, text="Email:").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.student_email_entry = ctk.CTkEntry(student_form_frame, width=200)
        self.student_email_entry.grid(row=2, column=3, padx=5, pady=5)
        
        ctk.CTkButton(add_student_frame, text="Add Student", command=self.add_student).pack(pady=10)
    
    def setup_registration_tab(self):
        """Setup the registration tab"""
        reg_frame = self.notebook.tab("Registration")
        
        # Registration Section
        register_frame = ctk.CTkFrame(reg_frame)
        register_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(register_frame, text="Student Registration", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Form
        reg_form_frame = ctk.CTkFrame(register_frame)
        reg_form_frame.pack(pady=10)
        
        ctk.CTkLabel(reg_form_frame, text="Student ID:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.reg_student_id_entry = ctk.CTkEntry(reg_form_frame, width=200)
        self.reg_student_id_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(reg_form_frame, text="Select Event:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.event_combobox = ctk.CTkComboBox(reg_form_frame, width=300)
        self.event_combobox.grid(row=1, column=1, padx=5, pady=5)
        
        button_reg_frame = ctk.CTkFrame(register_frame)
        button_reg_frame.pack(pady=10)
        
        ctk.CTkButton(button_reg_frame, text="Register Student", command=self.register_student).pack(side="left", padx=5)
        ctk.CTkButton(button_reg_frame, text="Mark Attendance", command=self.mark_attendance).pack(side="left", padx=5)
        ctk.CTkButton(button_reg_frame, text="Refresh Events", command=self.refresh_event_combobox).pack(side="left", padx=5)
        
        self.refresh_event_combobox()
    
    def setup_reports_tab(self):
        """Setup the reports tab"""
        reports_frame = self.notebook.tab("Reports")
        
        # Reports Section
        ctk.CTkLabel(reports_frame, text="Reports & Analytics", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        button_reports_frame = ctk.CTkFrame(reports_frame)
        button_reports_frame.pack(pady=10)
        
        ctk.CTkButton(button_reports_frame, text="Event Attendance Report", command=self.show_attendance_report).pack(side="left", padx=5)
        ctk.CTkButton(button_reports_frame, text="Department Participation", command=self.show_department_report).pack(side="left", padx=5)
        ctk.CTkButton(button_reports_frame, text="Export to Excel", command=self.export_reports).pack(side="left", padx=5)
        
        # Reports display frame
        self.reports_display_frame = ctk.CTkFrame(reports_frame)
        self.reports_display_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Event Management Methods
    def add_event(self):
        """Add a new event"""
        name = self.event_name_entry.get().strip()
        description = self.event_desc_entry.get().strip()
        date = self.event_date_entry.get().strip()
        location = self.event_location_entry.get().strip()
        
        if not all([name, date, location]):
            msgbox.showerror("Error", "Please fill in all required fields (Name, Date, Location)")
            return
        
        try:
            self.event_manager.add_event(name, description, date, location)
            msgbox.showinfo("Success", "Event added successfully!")
            
            # Clear form
            self.event_name_entry.delete(0, 'end')
            self.event_desc_entry.delete(0, 'end')
            self.event_date_entry.delete(0, 'end')
            self.event_location_entry.delete(0, 'end')
            
            self.refresh_events_list()
            self.refresh_event_combobox()
            
        except Exception as e:
            msgbox.showerror("Error", f"Failed to add event: {str(e)}")
    
    def refresh_events_list(self):
        """Refresh the events list"""
        # Clear existing items
        for item in self.events_tree.get_children():
            self.events_tree.delete(item)
        
        # Add events
        events = self.event_manager.get_all_events()
        for event in events:
            self.events_tree.insert("", "end", values=event)
    
    def delete_event(self):
        """Delete selected event"""
        selected = self.events_tree.selection()
        if not selected:
            msgbox.showwarning("Warning", "Please select an event to delete")
            return
        
        item = self.events_tree.item(selected[0])
        event_id = item['values'][0]
        event_name = item['values'][1]
        
        if msgbox.askyesno("Confirm", f"Are you sure you want to delete '{event_name}'?"):
            try:
                self.event_manager.delete_event(event_id)
                msgbox.showinfo("Success", "Event deleted successfully!")
                self.refresh_events_list()
                self.refresh_event_combobox()
            except Exception as e:
                msgbox.showerror("Error", f"Failed to delete event: {str(e)}")
    
    # Student Management Methods
    def add_student(self):
        """Add a single student"""
        student_id = self.student_id_entry.get().strip()
        first_name = self.student_fname_entry.get().strip()
        last_name = self.student_lname_entry.get().strip()
        department = self.student_dept_entry.get().strip()
        year_level = self.student_year_entry.get().strip()
        email = self.student_email_entry.get().strip()
        
        if not all([student_id, first_name, last_name, department, year_level]):
            msgbox.showerror("Error", "Please fill in all required fields")
            return
        
        try:
            year_level = int(year_level)
            self.student_manager.add_student(student_id, first_name, last_name, department, year_level, email)
            msgbox.showinfo("Success", "Student added successfully!")
            
            # Clear form
            self.student_id_entry.delete(0, 'end')
            self.student_fname_entry.delete(0, 'end')
            self.student_lname_entry.delete(0, 'end')
            self.student_dept_entry.delete(0, 'end')
            self.student_year_entry.delete(0, 'end')
            self.student_email_entry.delete(0, 'end')
            
        except ValueError:
            msgbox.showerror("Error", "Year level must be a number")
        except sqlite3.IntegrityError:
            msgbox.showerror("Error", "Student ID already exists")
        except Exception as e:
            msgbox.showerror("Error", f"Failed to add student: {str(e)}")
    
    def import_students(self):
        """Import students from Excel file"""
        file_path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        
        if file_path:
            try:
                count = self.student_manager.import_students_from_excel(file_path)
                msgbox.showinfo("Success", f"Successfully imported {count} students!")
            except Exception as e:
                msgbox.showerror("Error", f"Failed to import students: {str(e)}")
    
    def download_sample_excel(self):
        """Create and download a sample Excel file"""
        sample_data = {
            'student_id': ['2023001', '2023002', '2023003'],
            'first_name': ['John', 'Jane', 'Bob'],
            'last_name': ['Doe', 'Smith', 'Johnson'],
            'department': ['Computer Science', 'Engineering', 'Business'],
            'year_level': [1, 2, 3],
            'email': ['john.doe@email.com', 'jane.smith@email.com', 'bob.johnson@email.com']
        }
        
        df = pd.DataFrame(sample_data)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        
        if file_path:
            df.to_excel(file_path, index=False)
            msgbox.showinfo("Success", f"Sample file saved to {file_path}")
    
    # Registration Methods
    def register_student(self):
        """Register a student for an event"""
        student_id = self.reg_student_id_entry.get().strip()
        event_selection = self.event_combobox.get()
        
        if not student_id or not event_selection:
            msgbox.showerror("Error", "Please enter Student ID and select an event")
            return
        
        # Extract event ID from selection
        try:
            event_id = int(event_selection.split(" - ")[0])
        except:
            msgbox.showerror("Error", "Please select a valid event")
            return
        
        # Check if student exists
        student = self.student_manager.get_student(student_id)
        if not student:
            msgbox.showerror("Error", "Student not found. Please add the student first.")
            return
        
        try:
            self.registration_manager.register_student(event_id, student_id)
            msgbox.showinfo("Success", f"Student {student_id} registered successfully!")
            self.reg_student_id_entry.delete(0, 'end')
        except sqlite3.IntegrityError:
            msgbox.showerror("Error", "Student is already registered for this event")
        except Exception as e:
            msgbox.showerror("Error", f"Failed to register student: {str(e)}")
    
    def mark_attendance(self):
        """Mark student attendance"""
        student_id = self.reg_student_id_entry.get().strip()
        event_selection = self.event_combobox.get()
        
        if not student_id or not event_selection:
            msgbox.showerror("Error", "Please enter Student ID and select an event")
            return
        
        try:
            event_id = int(event_selection.split(" - ")[0])
            self.registration_manager.mark_attendance(event_id, student_id)
            msgbox.showinfo("Success", f"Attendance marked for student {student_id}")
            self.reg_student_id_entry.delete(0, 'end')
        except Exception as e:
            msgbox.showerror("Error", f"Failed to mark attendance: {str(e)}")
    
    def refresh_event_combobox(self):
        """Refresh the event combobox"""
        events = self.event_manager.get_all_events()
        event_options = [f"{event[0]} - {event[1]}" for event in events]
        self.event_combobox.configure(values=event_options)
    
    # Reports Methods
    def show_attendance_report(self):
        """Show attendance report"""
        # Clear previous content
        for widget in self.reports_display_frame.winfo_children():
            widget.destroy()
        
        stats = self.reports_manager.get_event_attendance_stats()
        
        if not stats:
            ctk.CTkLabel(self.reports_display_frame, text="No data available").pack(pady=20)
            return
        
        # Create report display
        report_text = ctk.CTkTextbox(self.reports_display_frame, width=600, height=300)
        report_text.pack(pady=20)
        
        report_content = "EVENT ATTENDANCE REPORT\n" + "="*50 + "\n\n"
        for stat in stats:
            event_name, registered, attended = stat
            attended = attended or 0
            report_content += f"Event: {event_name}\n"
            report_content += f"Registered: {registered}\n"
            report_content += f"Attended: {attended}\n"
            report_content += f"Attendance Rate: {(attended/registered*100) if registered > 0 else 0:.1f}%\n\n"
        
        report_text.insert("0.0", report_content)
        report_text.configure(state="disabled")
    
    def show_department_report(self):
        """Show department participation report"""
        # Clear previous content
        for widget in self.reports_display_frame.winfo_children():
            widget.destroy()
        
        stats = self.reports_manager.get_department_participation()
        
        if not stats:
            ctk.CTkLabel(self.reports_display_frame, text="No data available").pack(pady=20)
            return
        
        # Create report display
        report_text = ctk.CTkTextbox(self.reports_display_frame, width=600, height=300)
        report_text.pack(pady=20)
        
        report_content = "DEPARTMENT PARTICIPATION REPORT\n" + "="*50 + "\n\n"
        total_registrations = sum(stat[1] for stat in stats)
        
        for stat in stats:
            department, registrations = stat
            percentage = (registrations/total_registrations*100) if total_registrations > 0 else 0
            report_content += f"Department: {department}\n"
            report_content += f"Registrations: {registrations}\n"
            report_content += f"Percentage: {percentage:.1f}%\n\n"
        
        report_text.insert("0.0", report_content)
        report_text.configure(state="disabled")
    
    def export_reports(self):
        """Export reports to Excel"""
        try:
            # Get attendance stats
            attendance_stats = self.reports_manager.get_event_attendance_stats()
            dept_stats = self.reports_manager.get_department_participation()
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")]
            )
            
            if file_path:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # Attendance report
                    if attendance_stats:
                        att_df = pd.DataFrame(attendance_stats, 
                                            columns=['Event Name', 'Total Registered', 'Total Attended'])
                        att_df.to_excel(writer, sheet_name='Attendance Report', index=False)
                    
                    # Department report
                    if dept_stats:
                        dept_df = pd.DataFrame(dept_stats, 
                                             columns=['Department', 'Registrations'])
                        dept_df.to_excel(writer, sheet_name='Department Report', index=False)
                
                msgbox.showinfo("Success", f"Reports exported to {file_path}")
        except Exception as e:
            msgbox.showerror("Error", f"Failed to export reports: {str(e)}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

# Main execution
if __name__ == "__main__":
    app = CampusEventApp()
    app.run()