# PyInstaller spec for the TrackFlow desktop client.
# Build:  pyinstaller trackflow.spec
# Produces dist/TrackFlow.exe (Windows) or dist/TrackFlow.app (macOS).
import sys

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources/style.qss', 'resources')],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TrackFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # GUI app: no console window
    disable_windowed_traceback=False,
    target_arch=None,        # universal2 set in CI for macOS if desired
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='TrackFlow.app',
        icon=None,
        bundle_identifier='com.trackflow.client',
        info_plist={
            'CFBundleName': 'TrackFlow',
            'CFBundleDisplayName': 'TrackFlow',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
