from datetime import datetime

def str_timestamp(val) -> float:
    try:
        if isinstance(val, datetime): 
            return val.timestamp()
        if val is None: 
            return 0.0
        return datetime.fromisoformat(str(val)).timestamp()
    except:
        return 0.0 # Se falhar, assume zero (data antiga)
    
def str_datetime(val) -> datetime:
    try:
        if isinstance(val, datetime):
            return val
        if val is None:
            return datetime.fromtimestamp(0)
        return datetime.fromisoformat(str(val))
    except:
        return datetime.fromtimestamp(0) # Se falhar, assume zero (data antiga)