import streamlit as st
import os
import time
import subprocess
import sys

# --- Playwright Installation for Streamlit Cloud ---
def install_playwright(force=False):
    if os.path.exists("playwright-installed.txt") and not force:
        return
        
    try:
        with st.spinner("Installing Playwright Browsers... (this may take a minute)"):
            # Install Chromium
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            
            # Create marker file
            with open("playwright-installed.txt", "w") as f:
                f.write("done")
            print("Playwright browsers installed.")
    except Exception as e:
        st.error(f"Error installing Playwright: {e}")

# Check on startup
install_playwright()

# Manual Re-install button for debugging
if st.sidebar.button("Re-install Browser Binaries"):
    install_playwright(force=True)
    st.sidebar.success("Re-installation command sent. Please reload the app if it persists.")

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
                        "Details": "Success",
                        "Raw Output": output
                    })
                else:
                    st.session_state.results.append({
                        "File Name": uploaded_file.name,
                        "Status": "⚠️ Completed with Warning",
                        "Assumed URL": "-",
                        "Details": "Confirmation not found",
                        "Raw Output": output + "\n" + result.stderr
                    })
            else:
                 st.session_state.results.append({
                    "File Name": uploaded_file.name,
                    "Status": "❌ Failed",
                    "Assumed URL": "-",
                    "Details": "Error (Exit Code 1)",
                    "Raw Output": result.stderr
                })
                
        except Exception as e:
            st.session_state.results.append({
                "File Name": uploaded_file.name,
                "Status": "❌ Error",
                "Assumed URL": "-",
                "Details": str(e),
                "Raw Output": str(e)
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
    
    # Display main table
    st.dataframe(
        df[["File Name", "Status", "Assumed URL"]],
        column_config={
            "Assumed URL": st.column_config.LinkColumn("Assumed URL"),
        },
        use_container_width=True,
        hide_index=True,
    )
    
    # Error details below
    st.subheader("Logs & Details")
    for res in st.session_state.results:
        if res["Status"] != "✅ Success":
            unique_key = f"{res['File Name']}_{res['Status']}"
            with st.expander(f"Details for {res['File Name']} ({res['Status']})"):
                st.text("Details:")
                st.code(res["Details"])
                st.text("Full Output:")
                st.code(res.get("Raw Output", ""))
