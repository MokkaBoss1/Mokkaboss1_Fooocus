from flask import Flask, send_from_directory, render_template_string, request, jsonify, url_for, redirect
from PIL import Image
import os
import json
import webbrowser

app = Flask(__name__)
CONFIG_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'roots.json')

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
        #context-menu { display: none; position: fixed; background: #222; color: #fff; padding: 8px; border: 1px solid #444; border-radius: 4px; z-index: 1001; }
        #context-menu div { padding: 6px 12px; cursor: pointer; }
        #context-menu div:hover { background: #555; }
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
    </div>
    <div class="manage-button-container">
      <a class="manage-button" href="{{ url_for('manage_roots') }}">⚙️ Manage Buttons</a>
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
<div id="context-menu">
  <div onclick="copyImage()">📋 Copy</div>
  <div onclick="deleteImage()">🗑️ Del</div>
  <div onclick="saveImage()">💾 Save</div>
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
  });
  document.getElementById('viewer-img').oncontextmenu=e=>{
    e.preventDefault();
    const m=document.getElementById('context-menu');
    m.style.display='block';
    m.style.left=e.pageX+'px';
    m.style.top=e.pageY+'px';
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
