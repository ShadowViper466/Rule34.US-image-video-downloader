import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import tkinter.messagebox as messagebox
from tkinter import filedialog
import shutil
from tkinter import PhotoImage
from PIL import Image, ImageTk
import sys

# Global stop flag
stop_flag = False
is_completed = False

# Function to handle getting resources, even when bundled
def get_resource_path(relative_path):
    # If running as a PyInstaller bundle, use the temp folder
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Otherwise, use the script's directory
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

# Function to provide the PDF to the user
def provide_pdf():
    # Locate the bundled PDF
    source_pdf = get_resource_path("Help me Rule34.US.pdf")

    # Ask the user where to save the file
    save_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        title="Save Help PDF"
    )

    if not save_path:  # If the user cancels the dialog
        return

    try:
        # Copy the PDF to the chosen location
        shutil.copyfile(source_pdf, save_path)
        messagebox.showinfo("Download Complete", f"The PDF has been saved to:\n{save_path}")
    except IOError as e:
        messagebox.showerror("Error", f"Failed to save the PDF: {e}")

# Function to handle the focus event
def handle_url_focus(event):
    """Clear the default text when the user clicks on the URL field."""
    url_entry.delete(0, tk.END)  # Clear the default text

# Function to paste but block typing
def disable_typing(event):
    """Prevent typing but allow pasting."""
    if event.keysym not in ("Control_L", "Control_R", "v", "V"):  # Allow only paste (Ctrl+V)
        return "break"   

def clean_url(url, base_url):
    """Clean the URL to ensure it's absolute."""
    if url.startswith('http'):
        return url
    return urljoin(base_url, url)

def download_media(media_url, media_type, page_folder, base_url):
    """Download image, GIF, or video"""
    global stop_flag
    if stop_flag:
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    media_url = clean_url(media_url, base_url)
    media_name = os.path.basename(media_url)

    # Determine if the file should be skipped based on its extension
    if media_type == "IMG" and not media_name.lower().endswith(('.png', '.jpeg', '.jpg', '.gif')):
        print(f"Skipping non-image file: {media_name}")
        return
    elif media_type == "VIDS" and not media_name.lower().endswith(('.mp4', '.webm')):
        print(f"Skipping non-video file: {media_name}")
        return

    media_folder = os.path.join(page_folder, media_type)
    if not os.path.exists(media_folder):
        os.makedirs(media_folder)

    try:
        response = requests.get(media_url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(os.path.join(media_folder, media_name), "wb") as media_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if stop_flag:
                        return
                    media_file.write(chunk)
            print(f"Downloaded {media_type} media: {media_name}")
        else:
            print(f"Failed to download {media_type} media: {media_url} (Status Code: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {media_type} media {media_name}: {e}")

def download_siteL_image(page_folder, post_url, base_url):
    """Download the siteL.png image"""
    global stop_flag
    if stop_flag:
        return

    siteL_url = f"{post_url}siteL.png"
    siteL_url = clean_url(siteL_url, base_url)
    media_name = "siteL.png"

    media_folder = os.path.join(page_folder, "IMG")
    if not os.path.exists(media_folder):
        os.makedirs(media_folder)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        response = requests.get(siteL_url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(os.path.join(media_folder, media_name), "wb") as media_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if stop_flag:
                        return
                    media_file.write(chunk)
            print(f"Downloaded siteL.png: {media_name}")
        else:
            print(f"Failed to download siteL.png: {siteL_url} (Status Code: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading siteL.png: {e}")

def scrape_post_page(post_url, page_folder, executor, base_url):
    global stop_flag
    if stop_flag:
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        response = requests.get(post_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to retrieve post page: {post_url} (Status Code: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        img_tags = soup.find_all("img", {"src": True})
        
        # Download siteL.png as the 43rd item
        download_siteL_image(page_folder, post_url, base_url)
        
        for img_tag in img_tags:
            if stop_flag:
                return
            img_url = img_tag["src"]
            if img_url.lower().endswith(('.png', '.jpeg', '.jpg', '.gif')):  # Process only valid image files
                media_url = urljoin(post_url, img_url)
                executor.submit(download_media, media_url, "IMG", page_folder, base_url)

        video_tags = soup.find_all("video")
        for video_tag in video_tags:
            if stop_flag:
                return
            sources = video_tag.find_all("source")
            webm_url = None
            mp4_url = None

            for source in sources:
                video_url = source.get("src")
                if video_url and video_url.lower().endswith(".webm"):
                    webm_url = urljoin(post_url, video_url)
                elif video_url and video_url.lower().endswith(".mp4"):
                    mp4_url = urljoin(post_url, video_url)

            if webm_url:
                executor.submit(download_media, webm_url, "VIDS", page_folder, base_url)
            elif mp4_url:
                executor.submit(download_media, mp4_url, "VIDS", page_folder, base_url)

    except requests.exceptions.RequestException as e:
        print(f"Error processing post page {post_url}: {e}")

def scrape_list_page(list_page_url, page_folder, executor, base_url):
    global stop_flag
    if stop_flag:
        return

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        response = requests.get(list_page_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to retrieve list page: {list_page_url} (Status Code: {response.status_code})")
            return

        soup = BeautifulSoup(response.text, "html.parser")
        post_links = soup.find_all("a", {"href": True})
        
        for link in post_links:
            if stop_flag:
                return
            post_url = urljoin(list_page_url, link["href"])
            if "view&id=" in post_url:
                print(f"Processing post: {post_url}")
                scrape_post_page(post_url, page_folder, executor, base_url)
    except requests.exceptions.RequestException as e:
        print(f"Error processing list page {list_page_url}: {e}")

def get_character_name(base_url):
    """Retrieve the character name from the input field."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(base_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch character name. Status Code: {response.status_code}")
            return "UnknownCharacter"
        
        soup = BeautifulSoup(response.text, "html.parser")
        input_tag = soup.find("input", {"id": "tags"})
        if input_tag and input_tag.get("value"):
            return input_tag["value"].strip()
    except Exception as e:
        print(f"Error retrieving character name: {e}")
    return "UnknownCharacter"

def scrape_pages(start_page, end_page, base_url, base_folder):
    global stop_flag, is_completed
    character_name = get_character_name(base_url)
    base_folder = os.path.join(base_folder, "rule34.us", character_name)
    os.makedirs(base_folder, exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for page_num in range(start_page, end_page + 1):
            if stop_flag:
                break  # Stop if the stop flag is set
            page_folder = os.path.join(base_folder, f"page{page_num + 1}")
            os.makedirs(page_folder, exist_ok=True)

            page_url = f"{base_url}{character_name.replace(' ', '+')}&page={page_num}"
            print(f"Scraping page {page_num + 1}: {page_url}")
            scrape_list_page(page_url, page_folder, executor, base_url)

    # Only set this to True if scraping completes without interruption
    if not stop_flag:
        is_completed = True
        on_download_complete()  # Completion message
    else:
        print("Scraping was manually stopped.")

    # Once download is done, set the flag to stop further actions and re-enable buttons
    stop_flag = True
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    url_entry.config(state=tk.NORMAL)
    start_page_entry.config(state=tk.NORMAL)
    end_page_entry.config(state=tk.NORMAL)
    folder_entry.config(state=tk.NORMAL)
    folder_button.config(state=tk.NORMAL)

    print("Scraping completed successfully.")
    on_download_complete()

def on_download_complete():
    """Show a completion message only if the process finished normally"""
    global is_completed  # Reference the global variable
    if is_completed:
        messagebox.showinfo("Download Complete", "All images and videos have been successfully downloaded!")
        is_completed = False  # Reset the flag after showing the message

# GUI Code
def select_folder():
    folder_path = filedialog.askdirectory()
    if folder_path:
        folder_entry.config(state=tk.NORMAL)
        folder_entry.delete(0, tk.END)
        folder_entry.insert(0, folder_path)
        folder_entry.config(state="readonly")

def show_completion_message():
    """Show a message when the download is complete."""
    messagebox.showinfo("Download Complete", "All images and videos have been successfully downloaded!")

def stop_scraping():
    global stop_flag, is_completed
    stop_flag = True  # Set the stop flag to true to stop the download

    # Show "Download Stopped" message
    messagebox.showinfo("Download Stopped", "The download process has been stopped.")
    
    # Set completion flag to False because download was stopped manually
    is_completed = False

    # Disable all buttons and reset UI
    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    url_entry.config(state=tk.NORMAL)
    start_page_entry.config(state=tk.NORMAL)
    end_page_entry.config(state=tk.NORMAL)
    folder_entry.config(state=tk.NORMAL)
    folder_button.config(state=tk.NORMAL)
        # Make sure the hover effect is cleared when the button is disabled
    stop_button.config(bg="SystemButtonFace", fg="black")  # Reset stop button appearance

def start_scraping_thread():
    global stop_flag
    stop_flag = False

    url = url_entry.get()

    # Validate URL
    if not url.startswith("https://rule34.us"):
        messagebox.showerror("Invalid URL", "The base URL must be from https://rule34.us")
        return

    start_page = int(start_page_entry.get())
    end_page = int(end_page_entry.get())
    destination_folder = folder_entry.get()

    if not os.path.isdir(destination_folder):
        messagebox.showerror("Invalid folder", "The selected folder is invalid.")
        return

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)  # Enable the stop button when the download starts
    url_entry.config(state=tk.DISABLED)
    start_page_entry.config(state=tk.DISABLED)
    end_page_entry.config(state=tk.DISABLED)
    folder_entry.config(state=tk.DISABLED)
    folder_button.config(state=tk.DISABLED)
        # Make sure the hover effect is cleared when the button is disabled
    start_button.config(bg="SystemButtonFace", fg="black")  # Reset start button appearance


    threading.Thread(target=scrape_pages, args=(start_page, end_page, url, destination_folder)).start()

# Hover effect functions
def on_enter(event):
    if event.widget['state'] == tk.NORMAL:  # Check if the button is enabled
        event.widget.config(bg="#345434", fg="white")  # Change to green with white text

def on_leave(event):
    if event.widget['state'] == tk.NORMAL:  # Check if the button is enabled
        event.widget.config(bg="SystemButtonFace", fg="black")  # Revert to default appearance

#For Stop Button
def on_enter2(event):
    if event.widget.cget("state") == "normal":  # Check if the button is enabled
        event.widget.config(bg="#345434", fg="white")  # Change to green with white text
        closeProgram_button.config(bg="red")  # Change color to red on hover

def on_leave2(event):
    if event.widget.cget("state") == "normal":  # Check if the button is enabled
        event.widget.config(bg="SystemButtonFace", fg="black")  # Revert to default appearance
        closeProgram_button.config(bg="#344434")  # Change color back when hover ends

def resource_path(relative_path):
    """Get the absolute path to the resource, works for dev and bundled exe."""
    try:
        # If running as a bundled exe
        base_path = sys._MEIPASS
    except Exception:
        # If running as a script
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def close_window():
    root.quit()

    # Function to make the window draggable
def on_drag(event):
    x = root.winfo_pointerx() - root._offset_x
    y = root.winfo_pointery() - root._offset_y
    root.geometry(f'+{x}+{y}')

def on_press(event):
    root._offset_x = root.winfo_pointerx() - root.winfo_rootx()
    root._offset_y = root.winfo_pointery() - root.winfo_rooty()

# Function to get the correct path to the icon
def resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # In normal mode, return the current working directory
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# GUI Setup
root = tk.Tk()
root.title("Rule34.US Image/Video Downloader")
root.geometry("400x600")
root.overrideredirect(True)
root.resizable(False, False)
root.configure(bg="#344434")
button_font = ('Arial', 12)
label_font = ('Helvetica', 12)
button_font2 =('Arial', 10)
window_width = 400
window_height = 600
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_top = int(screen_height / 2 - window_height / 2)
position_left = int(screen_width / 2 - window_width / 2)
root.geometry(f"{window_width}x{window_height}+{position_left}+{position_top}")
if getattr(sys, 'frozen', False):
    # If running as a bundled .exe
    base_path = sys._MEIPASS
else:
    # If running as a script
    base_path = os.path.dirname(__file__)

# Access the files
image_path = os.path.join(base_path, "Rule34.US.png")




# Set the background color to match the image's transparency or desired color
root.config(bg='#344434')  # Set to your desired color

# Get the image path from the resource folder or bundled executable
image_path = resource_path("Rule34.US.png")

try:
    # Open the image file with transparency support (RGBA)
    img = Image.open(image_path).convert("RGBA")  # Convert to RGBA to handle transparency

    # Resize the image to fit
    max_size = (300, 200)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert the image to a Tkinter-compatible format
    image = ImageTk.PhotoImage(img)

    # Create a Canvas widget
    canvas = tk.Canvas(root, width=img.width, height=img.height, bg='#344434', bd=0, highlightthickness=0)
    canvas.pack(pady=10)

    # Display the image on the canvas
    canvas.create_image(0, 0, anchor=tk.NW, image=image)

except FileNotFoundError:
    print(f"Error: Image file '{image_path}' not found.")
    image = None

# If image loading failed, show a fallback message
if image is None:
    fallback_label = tk.Label(root, text="Image not found", bg='#344434', fg="white")
    fallback_label.pack(pady=10)

# URL entry
url_label = tk.Label(root, text="Enter URL here:", font=label_font)
url_label.pack(pady=5)
url_entry = tk.Entry(root, width=50, justify="center")
url_entry.pack(pady=5)
url_entry.insert(0, "Enter Rule34.US URL here!")
url_entry.bind("<FocusIn>", handle_url_focus)
url_entry.bind("<KeyPress>", disable_typing)

# Start and End Page
start_page_label = tk.Label(root, text="Start Page:", font=label_font)
start_page_label.pack(pady=5)
start_page_entry = tk.Entry(root, width=10, justify="center")
start_page_entry.pack(pady=5)

end_page_label = tk.Label(root, text="End Page:", font=label_font)
end_page_label.pack(pady=5)
end_page_entry = tk.Entry(root, width=10, justify="center")
end_page_entry.pack(pady=5)

# Folder Selection
folder_label = tk.Label(root, text="Select Folder:", font=label_font)
folder_label.pack(pady=5)
folder_button = tk.Button(root, text="Browse", command=select_folder, font=button_font)
folder_button.pack(pady=5)
folder_entry = tk.Entry(root, width=50, justify="center", state="readonly")
folder_entry.pack(pady=5)

# Start and Stop Buttons
start_button = tk.Button(root, text="Start Downloading", command=start_scraping_thread, font=button_font2)
start_button.pack(pady=5)

stop_button = tk.Button(root, text="Stop Downloading", command=stop_scraping, state=tk.DISABLED, font=button_font2)
stop_button.pack(pady=5)

help_button = tk.Button(root, text="Help how does this work?", command=provide_pdf, font=button_font2)
help_button.pack(pady=10)

closeProgram_button = tk.Button(root, text="X", command=close_window, bg="#344434", fg="white", relief="flat", font=("Arial", 12))
closeProgram_button.place(x=window_width - 50, y=10)


# Bind mouse press and drag events
root.bind("<Button-1>", on_press)
root.bind("<B1-Motion>", on_drag)

# Bind hover events to the Folder Button
folder_button.bind("<Enter>", on_enter)
folder_button.bind("<Leave>", on_leave)
# Bind hover events to the Start Button
start_button.bind("<Enter>", on_enter)
start_button.bind("<Leave>", on_leave)
# Bind hover events to the Stop Button
stop_button.bind("<Enter>", on_enter)
stop_button.bind("<Leave>", on_leave)
# Bind hover events to the Help Button
help_button.bind("<Enter>", on_enter)
help_button.bind("<Leave>", on_leave)
# Bind hover events to the CloseProgram Button
closeProgram_button.bind("<Enter>", on_enter2)
closeProgram_button.bind("<Leave>", on_leave2)

root.mainloop()
