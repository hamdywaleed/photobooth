import sqlite3
import random
from datetime import datetime, timedelta

DB_FILE = "photobooth.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# Clean up existing data first to start fresh
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM days")
    conn.commit()

# Branches
branches = ["Heaven", "9A"]

# Add initial stock
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
with get_db() as conn:
    cursor = conn.cursor()
    for branch in branches:
        cursor.execute('''
            INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
            VALUES (?, 'restock', ?, ?, ?)
        ''', (now_str, 5000, "رصيد افتتاحي للتجربة", branch))
    conn.commit()

# Pricing logic based on user request
options = [
    (1, 50.0), 
    (2, 90.0), 
    (3, 120.0) 
]

# Generate data for the last 60 days
start_date = datetime.now() - timedelta(days=60)

with get_db() as conn:
    cursor = conn.cursor()
    
    for day_offset in range(61):
        target_date = start_date + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Create day record
        cursor.execute("INSERT INTO days (date) VALUES (?)", (date_str,))
        day_id = cursor.lastrowid
        
        for branch in branches:
            # Different ranges to make them distinct. Say Heaven is slightly busier.
            if branch == "Heaven":
                num_customers = random.randint(15, 40)
            else:
                num_customers = random.randint(10, 30)
            
            for _ in range(num_customers):
                # Peak hours from 4 PM (16:00) to 11 PM (23:00)
                hour = random.randint(16, 23)
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                
                # Make sure we don't generate future times for today!
                tx_time = target_date.replace(hour=hour, minute=minute, second=second)
                if tx_time > datetime.now():
                    continue  # Skip future times so they don't break sorting today
                
                tx_time_str = tx_time.strftime("%Y-%m-%d %H:%M:%S")
                
                choice = random.choices(options, weights=[50, 30, 20])[0]
                prints, amount = choice
                
                cursor.execute('''
                    INSERT INTO transactions (day_id, timestamp, prints_count, amount_paid, branch)
                    VALUES (?, ?, ?, ?, ?)
                ''', (day_id, tx_time_str, prints, amount, branch))
                
                cursor.execute('''
                    INSERT INTO inventory (timestamp, action_type, quantity, notes, branch)
                    VALUES (?, 'consumption', ?, 'Transaction consumption', ?)
                ''', (tx_time_str, -prints, branch))
            
    conn.commit()

print("Dummy data for multiple branches inserted successfully.")
