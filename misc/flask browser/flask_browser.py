from flask import Flask, send_from_directory, render_template_string, request, jsonify, url_for, redirect
from PIL import Image
import os
import json
import webbrowser
import subprocess
import uuid

app = Flask(__name__)
CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'roots.json')
APPS_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'apps.json')

# Load or initialize roots configuration
def load_presets():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    # Defaults
    defaults = {
        "C Drive": r"C:/",
        "D Drive": r"D:/"
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(defaults, f, indent=4)
    return defaults

PRESET_FOLDERS = load_presets()

def save_presets():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(PRESET_FOLDERS, f, indent=4)

# Load or initialize apps configuration
def load_apps():
    if os.path.exists(APPS_FILE):
        try:
            with open(APPS_FILE, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception as e:
            print(f"Error loading apps: {e}")
    # Default apps
    defaults = [
        {"name": "Paint", "path": "mspaint.exe"},
        {"name": "Notepad", "path": "notepad.exe"}
    ]
    with open(APPS_FILE, 'w') as f:
        json.dump(defaults, f, indent=4)
    return defaults

def save_apps(apps):
    with open(APPS_FILE, 'w') as f:
        json.dump(apps, f, indent=4)

def get_image_size(path):
    try:
        with Image.open(path) as img:
            return img.size
    except:
        return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Mokkaboss1 Image Browser</title>
    <link href="https://fonts.googleapis.com/css2?family=Pacifico&display=swap" rel="stylesheet">
    <style>
        html { font-size: 16px; }
        body { margin: 0; background: #111; color: #eee; font-family: sans-serif; display: flex; flex-direction: column; height: 100vh; }
        a { color: #61dafb; text-decoration: none; }
        .root-button, .manage-button {
            margin: 10px;
            padding: 15px 30px;
            color: #fff;
            border-radius: 12px;
            font-size: 1.5rem;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.4);
            cursor: pointer;
        }
        .root-button {
            background: linear-gradient(135deg,#4e54c8,#8f94fb);
            transition: transform 0.2s ease;
        }
        .manage-button {
            background: linear-gradient(135deg,#28a745,#218838);
            transition: transform 0.2s ease;
        }
        .root-button:hover, .manage-button:hover {
            transform: scale(1.05);
        }
        .toolbar, .folders, .slider { background: #111; padding: 10px; }
        .toolbar { border-bottom: 2px solid #333; position: sticky; top: 0; z-index: 10; display: flex; flex-wrap: wrap; align-items: center; gap: 15px; }
        .toolbar input.path { flex: 1; background: #222; color: #eee; border: 1px solid #444; border-radius: 4px; padding: 5px; font-family: monospace; }
        .folders { border-bottom: 2px solid #222; display: flex; flex-wrap: wrap; gap: 10px; }
        .folder { margin: 5px; }
        .images { flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-wrap: wrap; gap: 10px; }
        .image { text-align: center; }
        .image img { width: var(--thumb-size,200px); border: 2px solid #444; border-radius: 8px; cursor: pointer; transition: width .2s ease; }
        .filename { font-size: .9rem; margin-top: 4px; }        #viewer { 
            display: none; 
            position: fixed; 
            top: 0; 
            left: 0; 
            width: 100%; 
            height: 100%; 
            background: rgba(0,0,0,0.95); 
            justify-content: center; 
            align-items: center; 
            flex-direction: column; 
            z-index: 1000; 
        }
        #viewer img { 
            max-width: 95%; 
            max-height: 90vh; 
            border: 4px solid #fff; 
            border-radius: 10px; 
            object-fit: contain;
            transition: all 0.3s ease-in-out;
        }
        /* Fullscreen-specific styling */
        #viewer.fullscreen img {
            max-width: 95vw;
            max-height: 90vh;
            object-fit: contain;
        }
        /* Slideshow progress indicator */
        #slideshow-progress {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 1010;
        }
        #slideshow-progress.visible {
            opacity: 1;
        }
        #close-btn { position: absolute; top: 10px; right: 20px; color: #fff; font-size: 24px; cursor: pointer; }
        #context-menu { display: none; position: fixed; background: #222; color: #fff; padding: 8px; border: 1px solid #444; border-radius: 4px; z-index: 1001; min-width: 150px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        #context-menu div { padding: 6px 12px; cursor: pointer; white-space: nowrap; }
        #context-menu div:hover { background: #555; }
        #open-with-apps-container { margin-top: 5px; }
        .manage-button-container { margin-top: auto; padding: 20px 20px 40px; text-align: center; }
        /* Slideshow controls fixed position */        #slideshow-controls {
            /* More compact and less intrusive design */
            display: flex !important; /* Force display */
            align-items: center;
            background: transparent;
            padding: 5px 10px;
            margin-left: 10px; 
            margin-right: auto; /* Push remaining elements right */
        }        #slideshow-controls input[type="number"] { 
            width: 50px; 
            margin-right: 8px;
            background: #333;
            color: white;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 4px;
        }
        #slideshow-controls label {
            color: #ddd;
            margin-right: 8px;
            user-select: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
        }
        #slideshow-controls input[type="checkbox"] {
            width: auto;
            margin-right: 4px;
            cursor: pointer;
        }
        #slideshow-controls .slideshow-icon { 
            cursor: pointer;
            font-size: 22px;
            margin-right: 8px;
            transition: all 0.2s ease-in-out;
            color: #8f94fb;
            padding: 4px;
            user-select: none;
        }
        #slideshow-controls .slideshow-icon:hover {
            transform: scale(1.15);
            color: #fff;
            text-shadow: 0 0 8px rgba(143, 148, 251, 0.6);
        }
        #slideshow-controls .slideshow-icon:active {
            transform: scale(0.95);
        }
    </style>
</head>
<body>
  {% if root_selection %}
  <div style="flex:1; display:flex; flex-direction:column; justify-content:flex-start; align-items:center; padding-top:40px;">
    <h1 style="font-family:'Pacifico',cursive; font-size:3.5rem; margin-bottom:40px;">
      Mokkaboss1 Image Browser
    </h1>
    <div style="display:flex; flex-wrap:wrap; justify-content:center; gap:20px;">
      {% for name in roots.keys() %}
        <a class="root-button" href="{{ url_for('browse', root=name, hide=1 if hide_names else 0, explode=1 if explode else 0, dims=1 if show_dims else 0, sort=sort, direction=direction) }}">{{ name }}</a>
      {% endfor %}
    </div>    <div class="manage-button-container">
      <a class="manage-button" href="{{ url_for('manage_roots') }}" style="margin-right: 10px;">⚙️ Manage Buttons</a>
      <a class="manage-button" href="{{ url_for('manage_apps') }}" style="background: linear-gradient(135deg,#8854c8,#af94fb);">🖥️ Manage Applications</a>
    </div>
  </div>
{% else %}  <div class="toolbar">
    <span style="font-family:'Pacifico',cursive; font-size:1.2rem; line-height:1; margin-right:10px;">Mokkaboss1 Image Browser</span>
    <a href="{{ url_for('home') }}">🏠 Root</a>
    {% if subpath %}
      <a href="{{ url_for('browse', root=root, subpath=parent or '', hide=1 if hide_names else 0, explode=1 if explode else 0, sort=sort, direction=direction, dims=1 if show_dims else 0) }}">⬆ Up</a>
    {% endif %}
      {# Slideshow controls directly in toolbar where they're more visible, only show when there are images #}    {% if images %}    <div id="slideshow-controls">      <span class="slideshow-icon" id="start-slideshow" title="Start Fullscreen Slideshow" role="button" tabindex="0">📷</span>
      <input id="slide-interval" type="number" min="0.5" value="1" step="0.5" title="Slideshow interval in seconds">
      <label title="Enable fade transitions between images"><input type="checkbox" id="fade-transition" checked> Fade</label>
    </div>
    {% endif %}
    <form id="optionsForm" method="get" action="{{ request.path }}">
      <label><input type="checkbox" name="hide" value="1" {% if hide_names %}checked{% endif %} onchange="this.form.submit()"> Hide filenames</label>
      <input type="hidden" name="hide" value="0">
      <label><input type="checkbox" name="explode" value="1" {% if explode %}checked{% endif %} onchange="this.form.submit()"> Explode folders</label>
      <label><input type="checkbox" name="dims" value="1" {% if show_dims %}checked{% endif %} onchange="this.form.submit()"> Show dimensions</label>
      <input type="hidden" name="sort" value="{{ sort }}">
      <input type="hidden" name="direction" value="{{ direction }}">
    </form>
    <span>Sort:</span>
    {% for s in ['name','date','size'] %}
      <button onclick="location.search='?hide={{1 if hide_names else 0}}&explode={{1 if explode else 0}}&dims={{1 if show_dims else 0}}&sort={{s}}&direction={{ 'asc' if sort!=s or direction=='desc' else 'desc' }}'">{{ s.capitalize() }}{% if sort==s %} {{ '▲' if direction=='asc' else '▼' }}{% endif %}</button>
    {% endfor %}
    <input class="path" type="text" readonly value="{{ current_path }}">
  </div>
  <div class="folders">
    {% for f in folders %}<div class="folder">📁 <a href="{{ url_for('browse', root=root, subpath=f['relpath'], hide=1 if hide_names else 0, explode=1 if explode else 0, sort=sort, direction=direction, dims=1 if show_dims else 0) }}">{{ f['name'] }}</a></div>{% endfor %}
  </div>
  <div class="slider">
    <label>📏 Size: <input type="range" id="sizeSlider" min="50" max="400" value="200" oninput="updateImageSize(this.value)"><span id="sliderValue">200</span>px</label>
  </div>  <div class="images">
    {% if images %}
      {% for img in images %}
        <div class="image">
          <img src="{{ url_for('file', root=root, fp=img['relpath']) }}" onclick="openViewer({{ loop.index0 }})" alt="{{ img['name'] }}">
          {% if not hide_names %}<div class="filename">{{ img['name'] }}</div>{% endif %}
          {% if show_dims and img['size'] %}<div class="filename">{{ img['size'][0] }}×{{ img['size'][1] }}</div>{% endif %}
        </div>
      {% endfor %}
    {% else %}
      <div style="width:100%; text-align:center; padding:40px; color:#aaa; font-size:1.2rem;">
        <div style="margin-bottom:15px; font-size:3rem;">📂</div>
        No images found in this folder. <br>
        <span style="font-size:0.9rem;">The slideshow controls will appear when images are available.</span>
      </div>
    {% endif %}
  </div>
{% endif %}

<div id="viewer" onclick="closeViewer()">
  <div id="close-btn" onclick="closeViewer()">✖</div>  <div id="viewer-controls-help" style="position:fixed; top:10px; left:10px; background:rgba(0,0,0,0.4); color:#ddd; 
              padding:6px 12px; border-radius:4px; font-size:0.8rem; opacity:0.6; text-align:left; 
              max-width:300px; transition:opacity 0.3s ease-in-out;">
    ← → Navigate • ESC/S Exit • P Toggle Slideshow • F Toggle F11 Fullscreen
  </div>
  <style>
    #viewer-controls-help:hover {
      opacity: 0.95 !important;
      background: rgba(0,0,0,0.7) !important;
      color: white !important;
    }
  </style>
  <img id="viewer-img" src="">
  <div id="slideshow-progress"></div>
</div>
<div id="context-menu">  <div onclick="copyImage()">📋 Copy</div>
  <div onclick="deleteImage()">🗑️ Del</div>
  <div onclick="saveImage()">💾 Save</div>
  <div id="open-with-apps-container">
    <!-- Apps will be loaded here dynamically -->
  </div>
</div>
<script>  // Initialize image arrays - ensure images exist
  const hasImages = {{ "true" if images else "false" }};
  const images = [{% for img in images %}"{{ url_for('file', root=root, fp=img['relpath']) }}"{% if not loop.last %}, {% endif %}{% endfor %}];
  const names  = [{% for img in images %}"{{ img['relpath'] }}"{% if not loop.last %}, {% endif %}{% endfor %}];
  let idx = 0, rootName = "{{ root }}";
    // Store timer in window object to ensure global scope access
  window.slideshowTimer = null;
  
  // Helper function to safely get/set the timer
  function getSlideshowTimer() {
    return window.slideshowTimer;
  }
  
  function setSlideshowTimer(timer) {
    window.slideshowTimer = timer;
    return timer;
  }
  
  function clearSlideshowTimer() {
    if (window.slideshowTimer) {
      clearInterval(window.slideshowTimer);
      window.slideshowTimer = null;
      return true;
    }
    return false;
  }
  
  // Define slideshowTimer as a getter/setter for window.slideshowTimer
  // This ensures we're always working with the same timer
  Object.defineProperty(window, 'slideshowTimer', {
    get: function() { return window._slideshowTimer; },
    set: function(value) { window._slideshowTimer = value; }
  });
  window._slideshowTimer = null;function openViewer(i) {
    try {
      console.log("Opening viewer for image index:", i);
      
      // Validate inputs to ensure they exist
      if (i === undefined || i === null || images.length === 0 || i >= images.length) {
        console.error("Invalid image index or empty images array:", i);
        return;
      }
      
      idx = i;
      const viewer = document.getElementById('viewer');
      if (!viewer) {
        console.error("Viewer element not found!");
        return;
      }
      
      const viewerImg = document.getElementById('viewer-img');
      if (!viewerImg) {
        console.error("Viewer image element not found!");
        return;
      }
        viewerImg.src = images[i];
      viewer.style.display = 'flex';
      
      // Add fullscreen class to support specific styling
      viewer.classList.add('fullscreen');
      
      // Ensure slideshow controls are visible in both normal and fullscreen modes
      const slideshowControls = document.getElementById('slideshow-controls');
    if (slideshowControls) {
      // Remove any existing cloned controls to avoid duplicates
      const existingClonedControls = viewer.querySelector('#viewer-controls-clone');
      if (existingClonedControls) {
        viewer.removeChild(existingClonedControls);
      }
        // Clone the controls and add to the viewer with special styling for fullscreen mode      const clonedControls = slideshowControls.cloneNode(true);
      clonedControls.id = 'viewer-controls-clone';
      clonedControls.style.display = 'flex';
      clonedControls.style.position = 'fixed'; 
      clonedControls.style.top = '10px';
      clonedControls.style.left = '10px';
      clonedControls.style.background = 'rgba(0,0,0,0.5)';
      clonedControls.style.padding = '12px';
      clonedControls.style.borderRadius = '4px';
      clonedControls.style.zIndex = '10000';
      clonedControls.style.boxShadow = '0 0 10px rgba(255,255,255,0.2)';
      
      // Fix duplicate ID issues by replacing IDs with classes in the cloned controls      const clonedIntervalInput = clonedControls.querySelector('input[type="number"]');
      if (clonedIntervalInput) {
        // Remove the duplicate ID
        clonedIntervalInput.removeAttribute('id');
        clonedIntervalInput.classList.add('slide-interval-clone');
      }
      
      // Also handle the fade checkbox in the cloned controls
      const clonedFadeCheckbox = clonedControls.querySelector('input[type="checkbox"]');
      const originalFadeCheckbox = document.getElementById('fade-transition');
      if (clonedFadeCheckbox && originalFadeCheckbox) {
        // Copy the checked state from the original
        clonedFadeCheckbox.checked = originalFadeCheckbox.checked;
        // Give it a class instead of ID
        clonedFadeCheckbox.removeAttribute('id');
        clonedFadeCheckbox.classList.add('fade-transition-clone');
      }
        
      // Set up event listeners for the cloned slideshow controls
      const clonedStartButton = clonedControls.querySelector('.slideshow-icon');
      if (clonedStartButton) {
        // Remove the original ID to avoid duplicate IDs in the document
        clonedStartButton.id = 'start-slideshow-clone';
        
        // Make sure it has the slideshow-icon class for proper event delegation
        clonedStartButton.classList.add('slideshow-icon');
        
        // Set correct initial appearance based on slideshow state
        if (slideshowTimer) {
          clonedStartButton.textContent = '⏹️';
          clonedStartButton.title = 'Stop Slideshow';
          clonedStartButton.style.color = '#ff7676';
        } else {
          clonedStartButton.textContent = '📷';
          clonedStartButton.title = 'Start Slideshow';
        }
      }        try {
          viewer.appendChild(clonedControls);
          console.log("Cloned slideshow controls added to viewer");
        } catch (err) {
          console.error("Error appending cloned controls:", err);
        }
      
        // After adding the cloned controls to the DOM, set up their event handlers
        setTimeout(refreshSlideshowIcons, 50); // Ensure DOM has processed the changes
      }
      // True full screen implementation (F11 equivalent)
      try {
        console.log("Attempting to enter true full screen mode (F11)");
        
        // Function to detect fullscreen state
        function isFullScreen() {
          return !!(document.fullscreenElement || document.mozFullScreenElement ||
            document.webkitFullscreenElement || document.msFullscreenElement);
        }
        
        // Function to properly toggle F11 style fullscreen
        function toggleTrueFullscreen() {
          // First try browser's native fullscreen API
          if (!isFullScreen()) {
            console.log("Entering true fullscreen mode");
            
            // Use F11 equivalent fullscreen
            const docEl = document.documentElement;
            
            if (docEl.requestFullscreen) {
              docEl.requestFullscreen();
            } else if (docEl.mozRequestFullScreen) { // Firefox
              docEl.mozRequestFullScreen();
            } else if (docEl.webkitRequestFullscreen) { // Chrome, Safari, Opera
              docEl.webkitRequestFullscreen();
            } else if (docEl.msRequestFullscreen) { // IE/Edge
              docEl.msRequestFullscreen();
            }
            
            // Make sure the viewer is properly sized for fullscreen
            setTimeout(() => {
              viewer.style.width = '100vw';
              viewer.style.height = '100vh';
              const viewerImg = document.getElementById('viewer-img');
              if (viewerImg) {
                viewerImg.style.maxWidth = '95vw';
                viewerImg.style.maxHeight = '90vh';
              }
            }, 100);
          }
        }
        
        // Enter true fullscreen (F11 equivalent)
        toggleTrueFullscreen();
        
        // Also apply fullscreen styling to the viewer itself as a fallback
        viewer.style.position = 'fixed';
        viewer.style.top = '0';
        viewer.style.left = '0';
        viewer.style.width = '100vw';
        viewer.style.height = '100vh';
        viewer.style.zIndex = '9999';
        viewer.style.backgroundColor = 'rgba(0,0,0,0.95)';
        
        // Make sure the image takes advantage of the full screen
        const viewerImg = document.getElementById('viewer-img');
        if (viewerImg) {
          viewerImg.style.maxWidth = '95vw';
          viewerImg.style.maxHeight = '90vh';
          viewerImg.style.objectFit = 'contain';
        }
        
        console.log("Full screen setup complete");
      } catch (err) {
        console.error("Error entering true fullscreen mode:", err);
      }
      
      console.log("Viewer opened successfully");
    } catch (err) {
      console.error("Error in openViewer():", err);
    }
  }function closeViewer() {
    console.log("Closing viewer, cleaning up resources");
    
    // Debug the current slideshow state before closing
    debugSlideshowState();
    
    // Clear the slideshow timer if it's running using our helper function
    if (clearSlideshowTimer()) {
      console.log("Slideshow timer cleared successfully");
      // For backward compatibility
      slideshowTimer = null;
    } else {
      console.log("No active slideshow timer to clear");
      // Force cleanup just to be safe
      if (window.slideshowTimer) {
        clearInterval(window.slideshowTimer);
        window.slideshowTimer = null;
        console.log("Forced timer cleanup");
      }
    }
      // Enhanced exit fullscreen implementation with cross-browser support
    try {      // Function to detect fullscreen state with cross-browser support
      function isFullScreen() {
        return !!(document.fullscreenElement || document.mozFullScreenElement ||
          document.webkitFullscreenElement || document.msFullscreenElement);
      }
      
      // Exit fullscreen using the appropriate method based on browser
      if (isFullScreen()) {
        console.log("Exiting fullscreen mode");
        try {
          // Try to use the browser's native exit fullscreen
          if (document.exitFullscreen) {
            document.exitFullscreen();
          } else if (document.mozCancelFullScreen) { // Firefox
            document.mozCancelFullScreen();
          } else if (document.webkitExitFullscreen) { // Chrome, Safari and Opera
            document.webkitExitFullscreen();
          } else if (document.msExitFullscreen) { // IE/Edge
            document.msExitFullscreen();
          }
        } catch (err) {
          console.warn('Exit fullscreen failed:', err);
        }
      }
      
      // Reset any fullscreen-like styling we might have applied as fallback
      const viewer = document.getElementById('viewer');
      viewer.style.position = '';
      viewer.style.top = '';
      viewer.style.left = '';
      viewer.style.width = '';
      viewer.style.height = '';
      viewer.style.backgroundColor = '';
      
      // Reset any image styles we modified
      const viewerImg = document.getElementById('viewer-img');
      if (viewerImg) {
        viewerImg.style.maxWidth = '';
        viewerImg.style.maxHeight = '';
        viewerImg.style.objectFit = '';
      }
    } catch (err) {
      console.error("Error exiting fullscreen mode:", err);
    }
    
    const viewer = document.getElementById('viewer');
    viewer.style.display = 'none';
    
    // Remove cloned controls with our new ID
    const clonedControls = viewer.querySelector('#viewer-controls-clone');
    if (clonedControls) {
      viewer.removeChild(clonedControls);
    }
    
    // Ensure event listeners are set up correctly after closing
    setTimeout(setupMainSlideshowControls, 100);
    
    // Ensure the original controls are visible in the toolbar
    const originalControls = document.getElementById('slideshow-controls');
    if (originalControls) {
      originalControls.style.display = 'flex';
    }    // Reset the icon state when slideshow is stopped
    const startIcons = document.querySelectorAll('#start-slideshow, #start-slideshow-clone, .slideshow-icon');
    startIcons.forEach(icon => {
      icon.textContent = '📷';
      icon.title = 'Start Slideshow';
      icon.style.color = '#8f94fb'; // Reset to original color
      
      // Important: Remove any inline onclick handlers that might have been added
      if (icon.hasAttribute('onclick')) {
        icon.removeAttribute('onclick');
      }
    });
      // Show all interval inputs again when slideshow is stopped
    const intervalInputs = document.querySelectorAll('input[type="number"]');
    intervalInputs.forEach(input => {
      input.style.display = 'inline-block';
    });
  }  // Toggle true F11-style fullscreen function
  function toggleFullscreen() {
    // Function to detect fullscreen state with cross-browser support
    function isFullScreen() {
      return !!(document.fullscreenElement || document.mozFullScreenElement ||
        document.webkitFullscreenElement || document.msFullscreenElement);
    }
    
    if (isFullScreen()) {
      // Exit fullscreen
      console.log("Exiting true fullscreen mode via toggle");
      try {
        if (document.exitFullscreen) {
          document.exitFullscreen();
        } else if (document.mozCancelFullScreen) {
          document.mozCancelFullScreen();
        } else if (document.webkitExitFullscreen) {
          document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
          document.msExitFullscreen();
        }
      } catch (err) {
        console.warn("Error exiting fullscreen:", err);
      }
    } else {
      // Enter fullscreen - use document element for true F11-style fullscreen
      console.log("Entering true F11-style fullscreen mode via toggle");
      try {
        const docEl = document.documentElement;
        
        if (docEl.requestFullscreen) {
          docEl.requestFullscreen();
        } else if (docEl.mozRequestFullScreen) {
          docEl.mozRequestFullScreen();
        } else if (docEl.webkitRequestFullscreen) {
          docEl.webkitRequestFullscreen();
        } else if (docEl.msRequestFullscreen) {
          docEl.msRequestFullscreen();
        }
      } catch (err) {
        console.warn("Error entering fullscreen:", err);
      }
    }
  }
  
  // Enhanced keyboard event handling
  document.addEventListener('keydown', e => {
    if (document.getElementById('viewer').style.display==='flex') {
      if(e.key==='ArrowRight') idx=(idx+1)%images.length;
      if(e.key==='ArrowLeft') idx=(idx-1+images.length)%images.length;
      if(e.key==='Escape' || e.key.toLowerCase()==='s') closeViewer();
      if(e.key.toLowerCase()==='f') toggleFullscreen(); // Add F key to toggle fullscreen
      document.getElementById('viewer-img').src=images[idx];
    }
  });// Handler function for slideshow icon clicks
  function handleSlideshowIconClick(e) {
    // Check if the clicked element is the start slideshow icon or a child element of it
    const isStartIcon = e.target.id === 'start-slideshow' || 
                        e.target.id === 'start-slideshow-clone' ||
                        e.target.closest('#start-slideshow') ||
                        e.target.classList.contains('slideshow-icon');
    
    if (isStartIcon) {
      console.log("Slideshow icon clicked:", e.target);
      e.stopPropagation(); // Prevent propagation to other handlers
      e.preventDefault(); // Prevent any default behavior
      
      // Ensure we run the actual slideshow function
      setTimeout(function() {
        startSlideshow(e);
      }, 0); // Use setTimeout to break out of the current event flow
    }
  }
  // Slideshow icon handlers with improved event management
  document.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded - setting up slideshow event handlers");
    
    // Set up the initial event listener for the camera icon
    setupMainSlideshowControls();
    
    // Add global delegation for any dynamically added icons
    // Use capture phase to ensure our handler runs before other click handlers
    document.addEventListener('click', handleSlideshowIconClick, true);
      // No direct binding - we'll rely solely on the delegated click handler
    const startIcon = document.getElementById('start-slideshow');
    if (startIcon) {
      console.log("Found start slideshow icon - using delegated handler only");
    }
    
    // Also handle keyboard access for better accessibility
    document.addEventListener('keydown', e => {
      if (e.target.classList.contains('slideshow-icon') && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        startSlideshow(e);
      }
      // Add shortcut key 'P' to toggle slideshow when in viewer mode
      if (document.getElementById('viewer').style.display === 'flex' && (e.key.toLowerCase() === 'p')) {
        e.preventDefault();
        console.log("Slideshow shortcut key pressed");
        startSlideshow();
      }
    });
    
    // Verify all slideshow icons are properly initialized after everything else is loaded
    setTimeout(function() {
      refreshSlideshowIcons();
      console.log("Initial slideshow setup complete");
    }, 500);
  });
  // Function to setup event listeners on the main slideshow controls
  function setupMainSlideshowControls() {
    console.log("Setting up main slideshow controls");
    
    // We'll now primarily rely on the global click handler to manage all slideshow icons
    // This function now just ensures the icon is properly set up visually
    const startIcon = document.getElementById('start-slideshow');
    if (startIcon) {      // Make sure the icon has the correct class
      startIcon.classList.add('slideshow-icon');
      // Make sure it has the correct initial appearance      startIcon.textContent = '📷';
      startIcon.title = 'Start Fullscreen Slideshow';
      
      // No direct binding - we rely only on the delegated handler
    }
      // Also set up the interval input
    const intervalInput = document.getElementById('slide-interval');
    if (intervalInput) {
      // Ensure it has a valid default value and constraints
      if (!intervalInput.value || parseFloat(intervalInput.value) < 0.5) {
        intervalInput.value = "1";
      }
      // Make sure min is set to 0.5 seconds
      intervalInput.min = "0.5";
      
      // Add validation to prevent values less than 0.5
      intervalInput.addEventListener('change', function() {
        const value = parseFloat(this.value);
        if (value < 0.5) {
          this.value = "0.5";
        }
      });
    }
  }
    // Enhanced function to start or stop the slideshow  // Enhanced function to start or stop the slideshow  // Helper function to ensure all slideshow icons have proper event handling
function refreshSlideshowIcons() {
  console.log("Refreshing slideshow icon event handlers");
  const allIcons = document.querySelectorAll('.slideshow-icon');
  const isActive = getSlideshowTimer() !== null;
  
  debugSlideshowState(); // Debug current state
    allIcons.forEach(icon => {
    // Remove any existing onclick handlers to avoid double-firing
    if (icon.hasAttribute('onclick')) {
      icon.removeAttribute('onclick');
    }
    // We're using delegated handlers only, so no direct binding here
    
    // Make sure it's keyboard accessible
    if (!icon.hasAttribute('tabindex')) {
      icon.setAttribute('tabindex', '0');
    }      // Make sure it's properly styled
    if (!icon.title) {
      icon.title = isActive ? "Stop Slideshow" : "Start Fullscreen Slideshow";
    }
    
    // Set the right appearance based on slideshow state
    if (isActive) {
      icon.textContent = '⏹️';
      icon.title = 'Stop Slideshow';
      icon.style.color = '#ff7676';
    } else {
      icon.textContent = '📷';
      icon.title = 'Start Fullscreen Slideshow';
      icon.style.color = '#8f94fb';
    }
  });
}

// Debug function to check slideshow state
function debugSlideshowState() {
  console.log("Current slideshow state:", {
    windowTimer: window.slideshowTimer,
    isActive: getSlideshowTimer() !== null,
    currentImageIndex: idx,
    totalImages: images.length,
    viewerVisible: document.getElementById('viewer').style.display === 'flex'
  });
}

function startSlideshow(e) {
    if (e) {
      e.stopPropagation();
      e.preventDefault(); // Prevent any default behavior
    }
    
    debugSlideshowState(); // Log current state for debugging
    
    // Get current timer state directly from window
    const currentTimer = getSlideshowTimer();
    console.log("Slideshow function called, current timer state:", currentTimer ? "running" : "stopped");
    
    // Toggle behavior - if slideshow is running, stop it
    if (currentTimer) {
      console.log("Stopping slideshow");
      closeViewer();
      return;
    }
    
    // Safety check - only proceed if we have images
    if (!hasImages || images.length === 0) {
      alert("No images available for slideshow");
      return;
    }
    
    // Find the interval input - check both original and cloned controls
    let intervalInput;
    
    // First try to find from the event target's container
    if (e && e.target) {
      const controlsContainer = e.target.closest('#slideshow-controls') || e.target.closest('#viewer-controls-clone');
      if (controlsContainer) {
        intervalInput = controlsContainer.querySelector('input[type="number"]');
      }
    }
    
    // If not found, try to get from document
    if (!intervalInput) {
      intervalInput = document.getElementById('slide-interval');
      // If in fullscreen mode, look for the cloned input
      if (!intervalInput) {
        const clonedControls = document.getElementById('viewer-controls-clone');
        if (clonedControls) {
          intervalInput = clonedControls.querySelector('input[type="number"]');
        }
      }
    }
      const sec = parseFloat(intervalInput ? intervalInput.value : 1) || 1;
    const interval = Math.max(sec * 1000, 500); // Ensure minimum interval of 500ms
    
    console.log("Starting slideshow with interval:", sec, "seconds");
      // Start from current image or reset to first
    try {
      const viewer = document.getElementById('viewer');
      if (!viewer) {
        console.error("Viewer element not found when starting slideshow");
        return;
      }
      
      if (viewer.style.display !== 'flex') {
        console.log("Viewer not currently displayed, opening with first image");
        idx = 0;
        
        // Try to open the viewer, but continue even if it fails
        try {
          openViewer(idx);
        } catch (viewerError) {
          console.error("Failed to open viewer:", viewerError);
          // Continue anyway to at least try setting up the timer
        }
      }
      else {
        console.log("Viewer already open, starting slideshow from current image:", idx);
      }
    } catch (err) {
      console.error("Error preparing viewer for slideshow:", err);
    }// Clear any existing timer and set new one
    clearSlideshowTimer();
    
    console.log("Starting slideshow timer with interval:", interval, "ms");
      try {
      console.log("Setting up slideshow timer to advance images automatically");
      
      // Verify we have images before starting the timer
      if (!images || images.length === 0) {
        console.error("No images available for slideshow timer");
        return;
      }      // Create a more robust interval function and store it using our helper
      const newTimer = setInterval(function() {
        try {
          console.log("Slideshow timer tick - advancing to next image");
          
          // Increment and wrap around
          idx = (idx + 1) % images.length;
          console.log(`Moving to image ${idx+1} of ${images.length}`);
          
          // Update progress indicator
          const progressIndicator = document.getElementById('slideshow-progress');
          if (progressIndicator) {
            progressIndicator.textContent = `Image ${idx+1} of ${images.length}`;
            progressIndicator.classList.add('visible');
            
            // Hide progress after a few seconds
            setTimeout(() => {
              progressIndicator.classList.remove('visible');
            }, 3000);
          }          // Get fade transition setting from either original or cloned checkbox
          let fadeCheckbox = document.getElementById('fade-transition');
          if (!fadeCheckbox) {
            // Try to find the cloned version
            const clonedCheckbox = document.querySelector('.fade-transition-clone');
            if (clonedCheckbox) {
              fadeCheckbox = clonedCheckbox;
            }
          }
          const fadeEnabled = fadeCheckbox ? fadeCheckbox.checked : false;
          
          // Update the image source with or without transition based on user preference
          const viewerImg = document.getElementById('viewer-img');
          if (viewerImg) {
            if (fadeEnabled) {
              // Apply fade transition
              viewerImg.style.opacity = '0.2';
              viewerImg.style.transition = 'opacity 0.3s ease-in-out';
              
              // Update src and fade back in after a short delay
              setTimeout(() => {
                viewerImg.src = images[idx];
                
                // Once the new image is loaded, fade it in
                viewerImg.onload = function() {
                  viewerImg.style.opacity = '1';
                  updateProgressIndicator();
                };
                
                // Safety fallback in case the onload event doesn't fire
                setTimeout(() => {
                  viewerImg.style.opacity = '1';
                }, 100);
                
                console.log("Advanced to image with fade:", idx+1, "of", images.length);
              }, 300);
            } else {
              // No fade - immediately update the image
              viewerImg.style.transition = 'none';
              viewerImg.style.opacity = '1';
              viewerImg.src = images[idx];
              updateProgressIndicator();
              console.log("Advanced to image without fade:", idx+1, "of", images.length);
            }
            
            // Helper function to update progress indicator
            function updateProgressIndicator() {
              // Show filename briefly with each new image
              const imageName = names[idx].split('/').pop();
              if (progressIndicator) {
                progressIndicator.textContent = `${imageName} (${idx+1}/${images.length})`;
                progressIndicator.classList.add('visible');
                
                setTimeout(() => {
                  progressIndicator.classList.remove('visible');
                }, 3000);
              }
            }
          } else {
            console.error("Viewer image element not found - stopping slideshow");
            clearSlideshowTimer(); // Emergency stop if viewer is gone
          }
        } catch (tickError) {
          console.error("Error in slideshow timer tick:", tickError);
        }
      }, interval);
      
      // Store the timer properly
      setSlideshowTimer(newTimer);
      
      // Verify timer was created
      if (getSlideshowTimer()) {
        console.log("Slideshow timer successfully created with ID:", getSlideshowTimer());
      } else {
        console.error("Failed to create slideshow timer!");
      }
    } catch (error) {
      console.error("Error setting up slideshow timer:", error);
    }    // Force immediate first image display and ensure fullscreen mode
    const viewerImg = document.getElementById('viewer-img');
    const viewer = document.getElementById('viewer');
    if (viewerImg) {
      console.log("Setting initial image in slideshow:", idx+1, "of", images.length);
      viewerImg.src = images[idx];
      
      // Show initial image name and progress
      const progressIndicator = document.getElementById('slideshow-progress');
      if (progressIndicator) {
        const imageName = names[idx].split('/').pop();
        progressIndicator.textContent = `${imageName} (${idx+1}/${images.length})`;
        progressIndicator.classList.add('visible');
        
        // Hide progress after a few seconds
        setTimeout(() => {
          progressIndicator.classList.remove('visible');
        }, 3000);
      }
      
      // Ensure we're in fullscreen mode for slideshow
      setTimeout(() => {
        if (viewer && !isFullScreen()) {
          console.log("Ensuring fullscreen mode for slideshow");
          // Function to detect fullscreen state with cross-browser support
          function isFullScreen() {
            return !!(document.fullscreenElement || document.mozFullScreenElement ||
              document.webkitFullscreenElement || document.msFullscreenElement);
          }
          
          // Try to enter fullscreen if not already in it
          if (viewer.requestFullscreen) {
            viewer.requestFullscreen().catch(err => console.warn('Fullscreen request in slideshow failed:', err));
          } else if (viewer.mozRequestFullScreen) {
            viewer.mozRequestFullScreen();
          } else if (viewer.webkitRequestFullscreen) {
            viewer.webkitRequestFullscreen();
          } else if (viewer.msRequestFullscreen) {
            viewer.msRequestFullscreen();
          }
        }
      }, 300); // Short delay to ensure the viewer is fully visible first
    }
    
    // Update icon to indicate slideshow is running and hide seconds input
    // Update both the original and cloned icons if they exist
    const startIcons = document.querySelectorAll('#start-slideshow, #start-slideshow-clone, .slideshow-icon');
    startIcons.forEach(icon => {
      // Change icon to indicate active slideshow
      icon.textContent = '⏹️';
      icon.title = 'Stop Slideshow';
      icon.style.color = '#ff7676'; // Red-ish color to indicate active state
    });
      // Hide all interval inputs while slideshow is active
    const intervalInputs = document.querySelectorAll('input[type="number"]');
    intervalInputs.forEach(input => {
      input.style.display = 'none';
    });
  }
  document.getElementById('viewer-img').oncontextmenu=e=>{
    e.preventDefault();
    const m=document.getElementById('context-menu');
    m.style.display='block';
    m.style.left=e.pageX+'px';
    m.style.top=e.pageY+'px';
    
    // Load applications directly into the context menu
    loadApplicationsIntoContextMenu();
  };
  document.addEventListener('click',()=>{document.getElementById('context-menu').style.display='none';});
  function copyImage(){
    fetch(images[idx]).then(r=>r.blob()).then(b=>navigator.clipboard.write([new ClipboardItem({[b.type]:b})]));
  }
  function deleteImage(){
    if(!confirm('Delete this image?')) return;
    fetch(`/delete/${rootName}/${names[idx]}`,{method:'POST'}).then(r=>r.json()).then(d=>{
      if(d.success){
        images.splice(idx,1);
        names.splice(idx,1);
        closeViewer();
        location.reload();
      }
    });
  }
  function saveImage(){
    const a=document.createElement('a');
    a.href=images[idx];
    a.download=names[idx].split('/').pop();
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
  function updateImageSize(v){
    document.documentElement.style.setProperty('--thumb-size',v+'px');
    document.getElementById('sliderValue').innerText=v;
  }  function loadApplicationsIntoContextMenu() {
    const appsContainer = document.getElementById('open-with-apps-container');
    
    // Clear any existing apps
    appsContainer.innerHTML = '';
    
    // Add a loading indicator
    const loadingDiv = document.createElement('div');
    loadingDiv.textContent = 'Loading apps...';
    loadingDiv.style.padding = '6px 12px';
    loadingDiv.style.color = '#aaa';
    appsContainer.appendChild(loadingDiv);
    
    // Get the list of applications
    fetch(`/open_with/${rootName}/${names[idx]}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({})
    })
    .then(r => r.json())
    .then(data => {
      // Remove loading indicator
      appsContainer.innerHTML = '';
      
      if (data.success && data.apps && data.apps.length > 0) {
        // Create menu items for each app
        data.apps.forEach(app => {
          const appDiv = document.createElement('div');
          appDiv.textContent = `🔄 ${app.name}`;
          appDiv.style.cursor = 'pointer';
          
          // Click handler
          appDiv.onclick = () => {
            // Hide the context menu
            document.getElementById('context-menu').style.display = 'none';
            
            // Create a feedback element
            const feedback = document.createElement('div');
            feedback.textContent = `Opening with ${app.name}...`;
            feedback.style.position = 'fixed';
            feedback.style.bottom = '20px';
            feedback.style.left = '50%';
            feedback.style.transform = 'translateX(-50%)';
            feedback.style.background = 'rgba(0,0,0,0.8)';
            feedback.style.color = 'white';
            feedback.style.padding = '10px 20px';
            feedback.style.borderRadius = '5px';
            feedback.style.zIndex = '2000';
            document.body.appendChild(feedback);
            
            // Send the request to open the file with this app
            fetch(`/open_with/${rootName}/${names[idx]}`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                appId: app.id
              })
            })
            .then(r => r.json())
            .then(result => {
              setTimeout(() => document.body.removeChild(feedback), 2000);
              if (!result.success && result.error) {
                alert('Error opening file: ' + result.error);
              }
            })
            .catch(err => {
              document.body.removeChild(feedback);
              alert('Error: ' + err);
            });
          };
          
          appsContainer.appendChild(appDiv);
        });
        
        // Add a divider
        const divider = document.createElement('div');
        divider.style.height = '1px';
        divider.style.backgroundColor = '#444';
        divider.style.margin = '5px 0';
        appsContainer.appendChild(divider);
        
        // Add "Manage apps" option
        const manageAppsDiv = document.createElement('div');
        manageAppsDiv.textContent = '➕ Manage apps...';
        manageAppsDiv.style.cursor = 'pointer';
        manageAppsDiv.onclick = () => {
          window.location.href = '/manage_apps';
        };
        appsContainer.appendChild(manageAppsDiv);
      } else {
        const noAppsDiv = document.createElement('div');
        noAppsDiv.textContent = '➕ Configure apps...';
        noAppsDiv.style.cursor = 'pointer';
        noAppsDiv.onclick = () => {
          window.location.href = '/manage_apps';
        };
        appsContainer.appendChild(noAppsDiv);
      }
    })
    .catch(err => {
      appsContainer.innerHTML = '';
      const errorDiv = document.createElement('div');
      errorDiv.textContent = 'Error loading apps';
      errorDiv.style.padding = '6px 12px';
      errorDiv.style.color = '#f55';
      appsContainer.appendChild(errorDiv);
    });
  }

  // After document is fully loaded, ensure all event handlers are properly set up
  window.addEventListener('load', function() {
    console.log("Window fully loaded - setting up all slideshow handlers");
    
    // Add MutationObserver to watch for changes in the DOM
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          // Check if any slideshow icons were added
          const hasAddedSlideshowIcons = Array.from(mutation.addedNodes).some(node => {
            return node.nodeType === 1 && (
              node.classList?.contains('slideshow-icon') || 
              node.querySelector?.('.slideshow-icon')
            );
          });
          
          if (hasAddedSlideshowIcons) {
            console.log("Slideshow icons added to DOM - refreshing handlers");
            setTimeout(refreshSlideshowIcons, 10); // Small delay to ensure DOM is ready
          }
        }
      });
    });
      // Start observing the document body for DOM changes
    observer.observe(document.body, { childList: true, subtree: true });
    
    // Initial setup of all slideshow icons - just refresh visual appearance, no direct handlers
    refreshSlideshowIcons();
    
    console.log("Using delegated click handler exclusively - no direct handlers added");
  });
</script>
</body>
</html>
"""

@app.route('/')
def home():
    hide_names = request.args.get('hide', '1') == '1'
    show_dims = request.args.get('dims', '0') == '1'
    sort = request.args.get('sort', 'size')
    direction = request.args.get('direction', 'desc')
    explode = request.args.get('explode', '0') == '1'
    return render_template_string(
        HTML_TEMPLATE,
        root_selection=True,
        roots=PRESET_FOLDERS,
        hide_names=hide_names,
        show_dims=show_dims,
        explode=explode,
        sort=sort,
        direction=direction
    )

@app.route('/browse/<root>/', defaults={'subpath': ''})
@app.route('/browse/<root>/<path:subpath>')
def browse(root, subpath):
    hide_names = request.args.get('hide', '1') == '1'
    show_dims = request.args.get('dims', '0') == '1'
    sort = request.args.get('sort', 'size')
    direction = request.args.get('direction', 'desc')
    explode = request.args.get('explode', '0') == '1'
    base = PRESET_FOLDERS.get(root)
    full_path = os.path.abspath(os.path.join(base or '', subpath))
    if not base or not os.path.exists(full_path):
        return "<h1>Not found</h1>", 404
    folders, images = [], []
    for entry in os.listdir(full_path):
        abs_e = os.path.join(full_path, entry)
        if os.path.isdir(abs_e):
            folders.append({'name': entry, 'relpath': os.path.relpath(abs_e, base).replace('\\','/')})
    walker = os.walk(full_path) if explode else [(full_path, [], os.listdir(full_path))]
    for dp, _, files in walker:
        for f in files:
            if f.lower().endswith(('.png','.jpg','.jpeg','.webp')):
                abs_p = os.path.join(dp, f)
                images.append({
                    'name': f,
                    'relpath': os.path.relpath(abs_p, base).replace('\\','/'),
                    'size': get_image_size(abs_p)
                })
    def sort_key(item):
        p = os.path.join(base, item['relpath'])
        if sort == 'size': return os.path.getsize(p)
        if sort == 'date': return os.path.getmtime(p)
        return item['name'].lower()
    images.sort(key=sort_key, reverse=(direction=='desc'))
    return render_template_string(
        HTML_TEMPLATE,
        root_selection=False,
        roots=PRESET_FOLDERS,
        hide_names=hide_names,
        show_dims=show_dims,
        explode=explode,
        folders=folders,
        images=images,
        root=root,
        subpath=subpath,
        sort=sort,
        direction=direction,
        parent=os.path.dirname(subpath),
        current_path=full_path
    )

@app.route('/files/<root>/<path:fp>')
def file(root, fp):
    base = PRESET_FOLDERS.get(root)
    abs_p = os.path.join(base or '', fp)
    return send_from_directory(os.path.dirname(abs_p), os.path.basename(abs_p))

@app.route('/delete/<root>/<path:fp>', methods=['POST'])
def delete_file(root, fp):
    base = PRESET_FOLDERS.get(root)
    abs_p = os.path.join(base or '', fp)
    try:
        os.remove(abs_p)
        return jsonify(success=True)
    except:
        return jsonify(success=False)

@app.route('/open_with/<root>/<path:fp>', methods=['POST'])
def open_with(root, fp):
    app_id = request.json.get('appId')
    
    base = PRESET_FOLDERS.get(root)
    abs_p = os.path.join(base or '', fp)
    
    if os.path.exists(abs_p):
        try:
            apps = load_apps()
            
            # If no app_id is provided, return the list of applications
            if app_id is None:
                return jsonify(success=True, apps=apps)
            
            # Find the selected app
            selected_app = None
            for app in apps:
                if app.get('id', str(apps.index(app))) == app_id:
                    selected_app = app
                    break
            
            if not selected_app:
                return jsonify(success=False, error="Application not found")
            
            # Get the command to execute
            app_path = selected_app.get('path')
            app_args = selected_app.get('args', '{file}')
            
            # Prepare the command
            quoted_path = '"' + abs_p + '"'
            if app_args and '{file}' in app_args:
                cmd = f'"{app_path}" {app_args.replace("{file}", quoted_path)}'
            else:
                cmd = f'"{app_path}" {quoted_path}'
            
            # Execute the application
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Run the application
            process = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            return jsonify(success=True)
                
        except Exception as e:
            return jsonify(success=False, error=str(e))
    return jsonify(success=False, error="File not found")

@app.route('/manage_apps', methods=['GET','POST'])
def manage_apps():
    msg = ''
    apps = load_apps()
    
    if request.method == 'POST':
        act = request.form.get('action')
        
        if act == 'add':
            name = request.form.get('name', '').strip()
            path = request.form.get('path', '').strip()
            args = request.form.get('args', '{file}').strip()
            
            if name and path:
                # Generate a unique ID for the app
                app_id = str(uuid.uuid4())[:8]
                
                apps.append({
                    "id": app_id,
                    "name": name,
                    "path": path,
                    "args": args
                })
                save_apps(apps)
                msg = f"Added application '{name}'"
            else:
                msg = "Invalid name or path"
                
        elif act == 'remove':
            app_id = request.form.get('app_id')
            if app_id:
                for i, app in enumerate(apps):
                    if app.get('id', str(i)) == app_id:
                        removed = apps.pop(i)
                        save_apps(apps)
                        msg = f"Removed application '{removed['name']}'"
                        break
        
        return redirect(url_for('manage_apps'))
    
    # Ensure all apps have IDs
    for i, app in enumerate(apps):
        if 'id' not in app:
            app['id'] = str(i)
    save_apps(apps)
    
    return render_template_string(
        """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Manage Applications</title>
          <link href="https://fonts.googleapis.com/css2?family=Pacifico&display=swap" rel="stylesheet">
          <style>
            html { font-size:16px; }
            body { margin:0; background:#111; color:#eee; font-family:sans-serif; display:flex; flex-direction:column; align-items:center; padding:20px; }
            h2 { font-family:'Pacifico',cursive; font-size:2.5rem; margin-bottom:20px; }
            form { background:#222; padding:15px; margin:10px; border-radius:8px; width:500px; }
            .app-list { background:#222; padding:15px; margin:10px; border-radius:8px; width:500px; }
            .app-item { display:flex; flex-direction:column; padding:15px; margin-bottom:15px; border:1px solid #444; border-radius:4px; position:relative; }
            .app-item-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
            label { display:block; margin:10px 0; font-size:1rem; }
            input, select { width:100%; padding:8px; border:1px solid #444; border-radius:4px; background:#111; color:#eee; }
            button { margin-top:10px; padding:10px 20px; background:linear-gradient(135deg,#8f94fb,#4e54c8); color:#fff; border:none; border-radius:8px; font-size:1rem; cursor:pointer; }
            .remove-btn { background:linear-gradient(135deg,#dc3545,#c82333); padding:5px 10px; font-size:0.8rem; position:absolute; top:12px; right:12px; margin-top:0; }
            button:hover { opacity:0.9; }
            a { margin-top:20px; color:#61dafb; text-decoration:none; font-size:1rem; }
            p { height:1.5rem; font-size:1rem; }
            .app-name { font-weight:bold; font-size:1.1rem; color:#fff; margin-bottom:10px; }
            .app-path { color:#aaa; font-size:0.9rem; word-break:break-all; margin-bottom:5px; padding:8px; background:#1a1a1a; border-radius:4px; }
            .path-label { color:#888; display:block; margin-bottom:2px; font-size:0.8rem; }
          </style>
        </head>
        <body>
        <h2>Manage Applications</h2>
        
        <form method="post">
          <h3 style="font-size:1.2rem;">Add Application</h3>
          <label>Application Name: <input name="name" placeholder="e.g. Paint"></label>
          <label>Path to Executable: <input name="path" placeholder="e.g. C:\\Windows\\System32\\mspaint.exe"></label>
          <button name="action" value="add">Add Application</button>
        </form>
        
        <div class="app-list">
          <h3 style="font-size:1.2rem;">Installed Applications</h3>
          {% for app in apps %}
          <div class="app-item">
            <div class="app-name">{{ app.name }}</div>
            <span class="path-label">Executable Path:</span>
            <div class="app-path">{{ app.path }}</div>
            {% if app.args and app.args != '{file}' %}
            <span class="path-label">Arguments:</span>
            <div class="app-path">{{ app.args }}</div>
            {% endif %}
            <form method="post" style="margin:0; background:none; width:auto; padding:0;">
              <input type="hidden" name="app_id" value="{{ app.id }}">
              <button class="remove-btn" name="action" value="remove">Remove</button>
            </form>
          </div>
          {% endfor %}
        </div>
        
        <p>{{ msg }}</p>
        <a href="{{ url_for('home') }}">← Back Home</a>
        </body>
        </html>
        """,
        apps=apps,
        msg=msg
    )
    
@app.route('/manage', methods=['GET','POST'])
def manage_roots():
    msg = ''
    if request.method == 'POST':
        act = request.form.get('action')
        name = request.form.get('name','').strip()
        path = request.form.get('path','').strip()
        if act == 'add':
            if name and path and os.path.isdir(path):
                PRESET_FOLDERS[name] = path
                msg = f"Added '{name}'"
            else:
                msg = 'Invalid name or path'
        elif act == 'remove':
            if name in PRESET_FOLDERS:
                PRESET_FOLDERS.pop(name)
                msg = f"Removed '{name}'"
            else:
                msg = 'Name not found'
        save_presets()
        return redirect(url_for('manage_roots'))

    return render_template_string(
        """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <title>Manage Buttons</title>
          <link href="https://fonts.googleapis.com/css2?family=Pacifico&display=swap" rel="stylesheet">
          <style>
            html { font-size:16px; }
            body { margin:0; background:#111; color:#eee; font-family:sans-serif; display:flex; flex-direction:column; align-items:center; padding:20px; }
            h2 { font-family:'Pacifico',cursive; font-size:2.5rem; margin-bottom:20px; }
            form { background:#222; padding:15px; margin:10px; border-radius:8px; width:300px; }
            label { display:block; margin:10px 0; font-size:1rem; }
            input, select { width:100%; padding:8px; border:1px solid #444; border-radius:4px; background:#111; color:#eee; }
            button { margin-top:10px; padding:10px 20px; background:linear-gradient(135deg,#8f94fb,#4e54c8); color:#fff; border:none; border-radius:8px; font-size:1rem; cursor:pointer; }
            button:hover { opacity:0.9; }
            a { margin-top:20px; color:#61dafb; text-decoration:none; font-size:1rem; }
            p { height:1.5rem; font-size:1rem; }
          </style>
        </head>
        <body>
        <h2>Manage Buttons</h2>
        <form method="post">
          <h3 style="font-size:1.2rem;">Add Button</h3>
          <label>Name: <input name="name"></label>
          <label>Path: <input name="path"></label>
          <button name="action" value="add">Add Button</button>
        </form>
        <form method="post">
          <h3 style="font-size:1.2rem;">Remove Button</h3>
          <label>Name:
            <select name="name">
              {% for n in roots.keys() %}
                <option>{{ n }}</option>
              {% endfor %}
            </select>
          </label>
          <button name="action" value="remove">Remove Button</button>
        </form>
        <p>{{ msg }}</p>
        <a href="{{ url_for('home') }}">← Back Home</a>
        </body>
        </html>
        """,
        roots=PRESET_FOLDERS,
        msg=msg
    )

if __name__ == '__main__':
    server_ip = '127.0.0.1'
    port = 5050
    print(f"Serving at http://{server_ip}:{port}/")
    webbrowser.open(f"http://{server_ip}:{port}/")
    app.run(host=server_ip, port=port, debug=False, threaded=True)
