import importlib.util
import os
import stat
import tempfile
from pathlib import Path
here=Path(__file__).resolve().parents[1]
os.environ['GI_TYPELIB_PATH']=str(here/'runtime/girepository-1.0')+os.pathsep+os.environ.get('GI_TYPELIB_PATH','')
spec=importlib.util.spec_from_file_location('khaos_hub_native',here/'app.py')
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
for uri in ('http://127.0.0.1:8766/','http://127.0.0.1:8766/library','http://127.0.0.1:8766/garage/'):
    assert app.is_local_hub_uri(uri),uri
for uri in ('https://127.0.0.1:8766/','http://localhost:8766/','http://127.0.0.1/','http://u@127.0.0.1:8766/','file:///etc/passwd','http://127.0.0.2:8766/'):
    assert not app.is_local_hub_uri(uri),uri
for uri in ('https://example.com','http://8.8.8.8'):
    assert app.HubWindow._is_safe_external_uri(uri),uri
for uri in ('file:///etc/passwd','http://127.0.0.1','http://192.168.1.1','http://localhost','http://host.local','https://user@example.com'):
    assert not app.HubWindow._is_safe_external_uri(uri),uri
with tempfile.TemporaryDirectory() as d:
    target=Path(d)/'private';app.prepare_private_dir(target)
    assert stat.S_IMODE(target.stat().st_mode)==0o700
    app.prepare_private_dir(target)
    assert stat.S_IMODE(target.stat().st_mode)==0o700
web=here.parent/'web'
html=(web/'index.html').read_text()
css=(web/'app.css').read_text()
assert 'icon-kimi-round-512.png' in html
assert (web/'icon-kimi-round-512.png').is_file()
assert (web/'still-water-glass.webp').is_file()
assert 'still-water-glass.webp' in css
assert 'prefers-reduced-transparency: reduce' in css
assert 'icon-kimi-64.rgba' in (here/'app.py').read_text()
assert 'set_icon_list([self.brand_pixbuf])' in (here/'app.py').read_text()
assert (here/'icon-kimi-64.rgba').stat().st_size == 64 * 64 * 4
assert 'Pixbuf.new_from_bytes' in (here/'app.py').read_text()
assert "StartupWMClass=KhaosHub" in (here/'install-user.sh').read_text()
print('native URI boundary, private profile, and visual asset checks passed')
