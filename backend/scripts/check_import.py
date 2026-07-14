import sys
import traceback
sys.path.insert(0, 'c:/SIMI-Task_Manager/backend')
try:
    import app
    print('imported app')
except Exception:
    traceback.print_exc()
