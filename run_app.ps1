# Launch the Streamlit app with correct Python path
# --server.address 0.0.0.0 allows access from other devices on your network
Write-Host "Starting Streamlit app..."
Write-Host "On this computer: http://localhost:8501"
Write-Host "On your phone: http://YOUR_IP:8501 (find IP with 'ipconfig')"
Write-Host ""
$env:PYTHONPATH = "."
.venv\Scripts\streamlit.exe run app\streamlit_app.py --server.address 0.0.0.0
