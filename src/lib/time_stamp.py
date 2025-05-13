from datetime import datetime

def get_current_timestamp():
    # 현재 시간을 밀리초 단위로 반환 (타임스탬프)
    return int(datetime.now().timestamp() * 1000)