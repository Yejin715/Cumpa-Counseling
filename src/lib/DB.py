import sqlite3
import os
import csv


def initialize():
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            speaker TEXT NOT NULL,
            content TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


def addMessage(speaker: str, content: str):
    if speaker not in ["USER", "AI", "PHASE"]:
        raise ValueError("speaker should be one of 'USER', 'AI', 'PHASE'.")
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (speaker, content) VALUES (?, ?)", (speaker, content)
    )
    conn.commit()
    conn.close()


def getHistory() -> str:
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT speaker, content FROM history")
    rows = cursor.fetchall()
    conn.close()

    temp = []
    for speaker, content in rows:
        if speaker == "PHASE":
            temp.append(f"\n[{content}]")
        else:
            temp.append(f"{speaker}: {content}")

    return "\n".join(temp)


def reset():
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM history")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='history'")
    conn.commit()
    conn.close()
    
    
def saveConversation(index: int, filepath: str):
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT speaker, content FROM history")
    rows = cursor.fetchall()
    conn.close()
    
    file_exists = os.path.exists(filepath)

    with open(filepath, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["index", "role", "message"])

        for row in rows:
            role, message = row
            if role != "PHASE":
                writer.writerow([index, role, message])