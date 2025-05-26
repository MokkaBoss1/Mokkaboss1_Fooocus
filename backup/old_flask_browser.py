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
        .filename { font-size: .9rem; margin-top: 4px; }
        #viewer { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); justify-content: center; align-items: center; flex-direction: column; z-index: 1000; }
        #viewer img { max-width: 95%; max-height: 95%; border: 4px solid #fff; border-radius: 10px; }
        #close-btn { position: absolute; top: 10px; right: 20px; color: #fff; font-size: 24px; cursor: pointer; }
        #context-menu { display: none; position: fixed; background: #222; color: #fff; padding: 8px; border: 1px solid #444; border-radius: 4px; z-index: 1001; min-width: 150px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
        #context-menu div { padding: 6px 12px; cursor: pointer; white-space: nowrap; }
        #context-menu div:hover { background: #555; }
        #open-with-apps-container { margin-top: 5px; }
        .manage-button-container { margin-top: auto; padding: 20px 20px 40px; text-align: center; }
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
{% else %}
  <div class="toolbar">
    <span style="font-family:'Pacifico',cursive; font-size:1.2rem; line-height:1; margin-right:10px;">Mokkaboss1 Image Browser</span>
    <a href="{{ url_for('home') }}">🏠 Root</a>
    {% if subpath %}<a href="{{ url_for('browse', root=root, subpath=parent or '', hide=1 if hide_names else 0, explode=1 if explode else 0, sort=sort, direction=direction, dims=1 if show_dims else 0) }}">⬆ Up</a>{% endif %}
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
  </div>
  <div class="images">
    {% for img in images %}
      <div class="image">
        <img src="{{ url_for('file', root=root, fp=img['relpath']) }}" onclick="openViewer({{ loop.index0 }})" alt="{{ img['name'] }}">
        {% if not hide_names %}<div class="filename">{{ img['name'] }}</div>{% endif %}
        {% if show_dims and img['size'] %}<div class="filename">{{ img['size'][0] }}×{{ img['size'][1] }}</div>{% endif %}
      </div>
    {% endfor %}
  </div>
{% endif %}

<div id="viewer" onclick="closeViewer()">
  <div id="close-btn" onclick="closeViewer()">✖</div>
  <img id="viewer-img" src="">
</div>
<div id="context-menu">  <div onclick="copyImage()">📋 Copy</div>
  <div onclick="deleteImage()">🗑️ Del</div>
  <div onclick="saveImage()">💾 Save</div>
  <div id="open-with-apps-container">
    <!-- Apps will be loaded here dynamically -->
  </div>
</div>
<script>
  const images = [{% for img in images %}"{{ url_for('file', root=root, fp=img['relpath']) }}"{% if not loop.last %}, {% endif %}{% endfor %}];
  const names  = [{% for img in images %}"{{ img['relpath'] }}"{% if not loop.last %}, {% endif %}{% endfor %}];
  let idx = 0, rootName = "{{ root }}";
  function openViewer(i) { idx = i; document.getElementById('viewer-img').src = images[i]; document.getElementById('viewer').style.display='flex'; }
  function closeViewer() { document.getElementById('viewer').style.display='none'; }
  document.addEventListener('keydown', e => {
    if (document.getElementById('viewer').style.display==='flex') {
      if(e.key==='ArrowRight') idx=(idx+1)%images.length;
      if(e.key==='ArrowLeft') idx=(idx-1+images.length)%images.length;
      if(e.key==='Escape') closeViewer();
      document.getElementById('viewer-img').src=images[idx];
    }
  });  document.getElementById('viewer-img').oncontextmenu=e=>{
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
