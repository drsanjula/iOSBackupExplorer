# 📱 iOS Backup Explorer

A modern PyQt6 desktop application to explore and export iOS backup files on macOS.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### Core Features
- 🖼️ **Camera Roll Export** - Bulk export photos & videos with original filenames
- 👥 **Contacts Export** - Export contacts to vCard (.vcf) format
- 💬 **Messages Export** - Export iMessage/SMS conversations to text files
- 📝 **Notes Export** - Export notes to text files
- 📞 **Call History** - Export call logs to CSV

### User Experience
- 🎨 **Modern UI** - Clean, native macOS look with system theme support (light/dark)
- 📊 **Statistics Dashboard** - See file counts, sizes, and breakdowns at a glance
- 👁️ **Image Preview** - Preview photos before exporting (Pro mode)
- 🔄 **Lite/Pro Modes** - Toggle between simple and full-featured interfaces
- 📁 **Multiple Backups** - Browse and manage multiple device backups

## 🚀 Quick Start

### One-Line Setup
```bash
git clone https://github.com/drsanjula/iOSBackupExplorer.git && cd iOSBackupExplorer && ./setup.sh
```

### Running the App
```bash
./run.sh
```

### Manual Installation
```bash
# Clone the repository
git clone https://github.com/drsanjula/iOSBackupExplorer.git
cd iOSBackupExplorer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## 📋 Requirements

- **macOS** 10.15 (Catalina) or later
- **Python** 3.10 or later
- **Unencrypted iOS backups** (created via Finder/iTunes)

### Full Disk Access

To access iOS backups, you may need to grant Full Disk Access:

1. Open **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Click **+** and add **Terminal** (or your Python interpreter)
3. Restart the application

## 📂 Backup Location

iOS backups are stored at:
```
~/Library/Application Support/MobileSync/Backup/
```

You can also browse custom backup locations using the "Browse Custom..." button.

## 🎯 Usage

1. **Launch the app** - Run `./run.sh` or `python main.py`
2. **Select a backup** - Choose from automatically discovered backups in the sidebar
3. **Choose data type** - Click on Camera Roll, Contacts, Messages, Notes, or Call History
4. **Browse content** - View files in the table, see statistics in the cards
5. **Preview files** - Select a file to see a preview (Pro mode, images only)
6. **Export** - Click "Export All" or select specific files and "Export Selected"

## 🔧 Modes

| Feature | Lite | Pro |
|---------|------|-----|
| Browse backups | ✅ | ✅ |
| Camera Roll export | ✅ | ✅ |
| Image preview | ❌ | ✅ |
| Contacts export | ❌ | ✅ |
| Messages export | ❌ | ✅ |
| Notes export | ❌ | ✅ |
| Call History export | ❌ | ✅ |

Toggle between modes using the Lite/Pro buttons in the sidebar.

## 📁 Project Structure

```
iOSBackupExplorer/
├── main.py                     # Application entry point
├── setup.sh                    # Setup script
├── run.sh                      # Run script
├── requirements.txt            # Python dependencies
├── src/
│   ├── core/
│   │   ├── backup_parser.py    # Manifest.db parser
│   │   └── data_extractors/
│   │       ├── camera_roll.py  # Photos & videos
│   │       ├── contacts.py     # Address book
│   │       ├── messages.py     # iMessage/SMS
│   │       ├── notes.py        # Notes app
│   │       └── call_history.py # Call logs
│   ├── ui/
│   │   ├── main_window.py      # Main application window
│   │   ├── sidebar.py          # Navigation sidebar
│   │   ├── content_view.py     # Content display area
│   │   ├── preview_panel.py    # Image preview panel
│   │   └── styles.py           # Qt stylesheets
│   └── utils/
│       ├── constants.py        # App constants
│       └── helpers.py          # Utility functions
└── resources/
    └── icons/                  # App icons
```

## 🔒 Privacy & Security

- **Local Only** - All processing happens locally on your Mac
- **No Network** - The app never connects to the internet
- **Read-Only** - Backups are read in read-only mode
- **Your Data** - Exported files are saved only where you choose

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🐛 Known Issues

- **Encrypted backups** are not supported (iOS backup encryption)
- **HEIC preview** may not work on older macOS versions
- **Very large backups** may take time to load initially

## 🙏 Acknowledgments

- Built with [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- iOS backup format documentation from the community
- Icons from native emoji set
