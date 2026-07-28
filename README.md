# 🏠 Nuestra Casita

Nuestra Casita is a Git-based household management project built around Grocy, Home Assistant, and automation.

The goal is to make it possible to recreate an entire household inventory system from scratch using version-controlled CSV files and Python automation.

---

# Features

- 📦 Product catalog stored in CSV
- 🛒 Automatic Grocy product importer
- 🏷 Product Group automation
- 📍 Location automation
- 🧮 Quantity Unit lookups
- 🔁 Duplicate protection
- 🔐 Secure API configuration using `.env`
- 📝 Git version controlled

---

# Project Structure

```
Nuestra-Casita/
│
├── catalog/
│   ├── products.csv
│   ├── recipes.csv
│   ├── chores.csv
│   ├── stores.csv
│   ├── locations.csv
│   └── shopping_preferences.csv
│
├── docs/
│
├── grocy/
│
├── home-assistant/
│
└── tools/
```

---

# Current Status

✅ Product Groups

✅ Shopping Locations

✅ Quantity Units

✅ Product Importer

✅ Duplicate Protection

⬜ Recipe Importer

⬜ Barcode Support

⬜ Shopping Preferences

⬜ Home Assistant Dashboard

⬜ Meal Planning

---

# Quick Start

Clone the repository.

Create a `.env` file.

Run:

```bash
python tools/setup_master_data.py
```

Import products:

```bash
python tools/import_products.py
```

---

# Roadmap

See:

```
docs/ROADMAP.md
```
