import sqlite3
import os
import csv


def initialize():
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS history (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            SPEAKER TEXT NOT NULL,
            CONTENT TEXT NOT NULL,
            START_TIME INTEGER NOT NULL,  -- 시작 시간 (타임스탬프)
            END_TIME INTEGER NOT NULL     -- 끝 시간 (타임스탬프)
        )
    """
    )
    conn.commit()
    conn.close()

def addMessage(SPEAKER: str, CONTENT: str, START_TIME: int, END_TIME: int):        
    if SPEAKER not in ["USER_KEYBOARD", "USER_WHISPER", "CUMPAR", "MODE_TURN", "PHASE"]:
        raise ValueError("speaker should be one of 'USER_KEYBOARD', 'USER_WHISPER', 'CUMPAR', 'MODE_TURN', 'PHASE'.")
    
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO history (SPEAKER, CONTENT, START_TIME, END_TIME) VALUES (?, ?, ?, ?)",
        (SPEAKER, CONTENT, START_TIME, END_TIME)
    )
    conn.commit()
    conn.close()


def getHistory() -> str:
    conn = sqlite3.connect("./src/lib/conversation_history.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SPEAKER, CONTENT, START_TIME, END_TIME FROM history")
    rows = cursor.fetchall()
    conn.close()

    temp = []
    for SPEAKER, CONTENT, START_TIME, END_TIME  in rows:
        if SPEAKER == "PHASE":
            temp.append(f"\n[{CONTENT}]")
        else:
            temp.append(f"{SPEAKER}: {CONTENT}: {START_TIME}: {END_TIME}")  # 시간 정보 추가

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
    cursor.execute("SELECT SPEAKER, CONTENT, START_TIME, END_TIME FROM history")
    rows = cursor.fetchall()
    conn.close()
    
    file_exists = os.path.exists(filepath)

    with open(filepath, mode='a', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)

        if not file_exists:
            writer.writerow(["INDEX", "ROLE", "MESSAGE", "START_TIME", "END_TIME"])  # 시간 추가

        for row in rows:
            ROLE, MESSAGE, START_TIME, END_TIME = row
            if ROLE != "PHASE":
                writer.writerow([index, ROLE, MESSAGE, START_TIME, END_TIME])  # 시간 정보 함께 저장