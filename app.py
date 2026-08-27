import sys 
from streamlit.web import cli as stcli

sys.argv = ["streamlit", "run", "teste.py"] 
sys.exit(stcli.main())

