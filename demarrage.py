import os
import subprocess
import threading
import time


def open_desktop_window():
  time.sleep(2.5)  # Brief pause to let Streamlit boot up
  # Launches Edge in standalone App Mode
  subprocess.run(['cmd', '/c', 'start msedge --app=http://localhost:8501'])


# Launch the browser in the background
threading.Thread(target=open_desktop_window, daemon=True).start()

# Set path and start Streamlit
os.chdir(r'C:\projects\PHARMACIEL')
os.system('streamlit run app.py')
