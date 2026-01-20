import streamlit as st
import os
import time
import subprocess
import sys

# --- Playwright Installation for Streamlit Cloud ---
def install_playwright():
    try:
        # Check if we can run a simple playwright command or if browsers exist
        # This is a basic check; usually running install is safe as it skips if present
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        print("Playwright browsers installed.")
    except Exception as e:
        print(f"Error installing Playwright browsers: {e}")

# Run installation once (naive check)
if not os.path.exists("playwright-installed.txt"): # limit re-runs
    install_playwright()
    # Create marker file
    with open("playwright-installed.txt", "w") as f:
        f.write("done")

st.set_page_config(page_title="PDF Bulk Uploader", layout="wide")

st.title("📂 PDF Bulk Uploader")
st.markdown("Upload multiple PDFs and automate their submission to the UCLA AMMP Form.")

if "results" not in st.session_state:
    st.session_state.results = []

uploaded_files = st.file_uploader("Choose PDF files", type=["pdf"], accept_multiple_files=True)

delay_seconds = st.sidebar.slider("Delay between uploads (seconds)", min_value=0, max_value=30, value=2)

start_btn = st.button("🚀 Start Upload Automation")

def process_uploads_subprocess(files):
    st.session_state.results = []
    
    # Create temp directory
    temp_dir = "temp_uploads"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_files = len(files)
    
    for i, uploaded_file in enumerate(files):
        file_path = os.path.join(temp_dir, uploaded_file.name)
        abs_file_path = os.path.abspath(file_path)
        
        # Save uploaded file locally
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        status_text.text(f"Processing ({i+1}/{total_files}): {uploaded_file.name}...")
        
        try:
            assumed_url = f"https://curtiscenter.math.ucla.edu/wp-content/uploads/ninja-forms/76/1/{uploaded_file.name}"
            
            # Execute the automation script as a subprocess
            # This isolates the Playwright event loop from Streamlit's loop
            cmd = [sys.executable, "form_automation.py", abs_file_path]
            
            # Run and capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Check STDOUT for success message
                # We look for "Submission successful! Response: ..."
                output = result.stdout
                if "Submission successful!" in output:
                     # Extract response text if possible or just show success
                    st.session_state.results.append({
                        "File Name": uploaded_file.name,
                        "Status": "✅ Success",
                        "Assumed URL": assumed_url,
                        "Details": "Processed via subprocess"
                    })
                else:
                    st.session_state.results.append({
                        "File Name": uploaded_file.name,
                        "Status": "⚠️ Completed with Warning",
                        "Assumed URL": "-",
                        "Details": "Script finished but success msg not found. Check logs."
                    })
            else:
                 st.session_state.results.append({
                    "File Name": uploaded_file.name,
                    "Status": "❌ Failed",
                    "Assumed URL": "-",
                    "Details": f"Error: {result.stderr}"
                })
                
        except Exception as e:
            st.session_state.results.append({
                "File Name": uploaded_file.name,
                "Status": "❌ Error",
                "Assumed URL": "-",
                "Details": str(e)
            })
        
        # Update Progress
        progress_bar.progress((i + 1) / total_files)
        
        # Delay logic
        if i < total_files - 1 and delay_seconds > 0:
            status_text.text(f"Waiting {delay_seconds} seconds...")
            time.sleep(delay_seconds)
        
    status_text.text("All files processed!")

if start_btn and uploaded_files:
    with st.spinner("Initializing Automation..."):
        process_uploads_subprocess(uploaded_files)

if st.session_state.results:
    st.subheader("Submission Results")
    
    # Convert to DataFrame for better display
    import pandas as pd
    df = pd.DataFrame(st.session_state.results)
    
    st.dataframe(
        df,
        column_config={
            "Status": st.column_config.TextColumn("Status", width="medium"),
            "Assumed URL": st.column_config.LinkColumn("Assumed URL", width="large"),
            "Details": st.column_config.TextColumn("Details", width="large"),
        },
        use_container_width=True,
        hide_index=True,
    )
