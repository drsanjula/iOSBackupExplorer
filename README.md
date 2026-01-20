# 📱 iOS Backup Explorer

A modern PyQt6 desktop application to explore and export iOS backup files on macOS.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

- 🖼️ **Camera Roll Export** - Bulk export photos & videos with original filenames
- 👥 **Contacts Export** - Export contacts to vCard format
- 💬 **Messages Export** - Export iMessage/SMS conversations
- 📝 **Notes Export** - Export notes to text/HTML
- 📞 **Call History** - View and export call logs
- 🎨 **Modern UI** - System theme support with Lite/Pro modes
- 📁 **Multiple Backups** - Browse and manage multiple device backups

## 🚀 Installation

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

- macOS 10.15+
- Python 3.10+
- Unencrypted iOS backups (created via Finder/iTunes)

## 📂 Default Backup Location

iOS backups are typically stored at:
```
~/Library/Application Support/MobileSync/Backup/
```

## 🎯 Usage

1. Launch the app
2. Select a backup from the sidebar (or browse custom location)
3. Choose data type (Camera Roll, Contacts, etc.)
4. Preview files (Pro mode)
5. Select destination folder and export

## 🔧 Modes

| Feature | Lite | Pro |
|---------|------|-----|
| Browse backups | ✅ | ✅ |
| Camera Roll export | ✅ | ✅ |
| Photo preview | ❌ | ✅ |
| Other data types | ❌ | ✅ |
| Date filtering | ❌ | ✅ |

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
