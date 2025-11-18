# Action Library Dimension Reference Guide

**File:** `categorized_action_library_improved.py`

This guide shows you exactly where to change widths, heights, and spacing in the Action Library.

---

## 📐 Action Card Dimensions

### Location: `ActionCard.__init__()` method (Lines 50-54)

```python
def setup_ui(self, color: str):
    # ... color setup code ...

    self.setCursor(Qt.PointingHandCursor)
    self.setMinimumHeight(50)        # ← LINE 51: Card minimum height
    self.setMaximumHeight(62)        # ← LINE 52: Card maximum height
    self.setMaximumWidth(200)        # ← LINE 54: Card maximum width
```

**Change here to adjust:**
- **Card Height**: Change values on lines 51-52
- **Card Width**: Change value on line 54

**Examples:**
```python
# Make cards taller:
self.setMinimumHeight(60)
self.setMaximumHeight(80)

# Make cards wider:
self.setMaximumWidth(250)

# Make cards narrower:
self.setMaximumWidth(150)
```

---

## 📏 Card Internal Spacing

### Location: `ActionCard.__init__()` method (Lines 56-59)

```python
# Main layout with minimal margins
layout = QVBoxLayout(self)
layout.setSpacing(2)                      # ← LINE 58: Space between name and description
layout.setContentsMargins(4, 4, 4, 4)     # ← LINE 59: Card padding (top, left, bottom, right)
```

**Change here to adjust:**
- **Spacing between labels**: Line 58
- **Card internal padding**: Line 59

**Examples:**
```python
# More space between name and description:
layout.setSpacing(4)

# More padding inside card:
layout.setContentsMargins(6, 6, 6, 6)

# Less padding (very tight):
layout.setContentsMargins(2, 2, 2, 2)
```

---

## 📝 Card Text Sizing

### Location: `ActionCard.__init__()` method

**Name Label (Lines 61-75):**
```python
self.name_label = QLabel(metadata.get("name", "Unknown"))
self.name_label.setStyleSheet(f"""
    QLabel {{
        color: {color};
        font-weight: bold;
        font-size: 11px;          # ← LINE 65: Name font size
        background: transparent;
        border: none;
        padding: 0px;             # ← LINE 68: Name label padding
    }}
""")
self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
self.name_label.setWordWrap(True)
self.name_label.setMaximumHeight(24)      # ← LINE 74: Name label max height
```

**Description Label (Lines 83-97):**
```python
self.desc_label = QLabel(desc)
self.desc_label.setStyleSheet("""
    QLabel {
        color: #555;
        font-size: 8px;           # ← LINE 87: Description font size
        background: transparent;
        border: none;
        padding: 0px;             # ← LINE 90: Description padding
        line-height: 1.1;
    }
""")
```

**Change here to adjust:**
- **Name font size**: Line 65
- **Description font size**: Line 87
- **Name height limit**: Line 74

---

## 📋 Category List Width

### Location: `CategorizedActionLibrary.setup_ui()` method (Line 315)

```python
# Left: Category list - NARROW
self.category_list = QListWidget()
self.category_list.setFixedWidth(100)     # ← LINE 315: Category list width
```

**Change here to adjust:**
- **Category list width**: Line 315

**Examples:**
```python
# Wider category list:
self.category_list.setFixedWidth(120)

# Narrower category list:
self.category_list.setFixedWidth(80)

# Original width:
self.category_list.setFixedWidth(160)
```

---

## 🎨 Category List Item Sizing

### Location: `CategoryListItem.__init__()` method (Lines 176-203)

```python
layout = QHBoxLayout(self)
layout.setContentsMargins(6, 5, 6, 5)     # ← LINE 176: Category item padding
layout.setSpacing(5)                      # ← LINE 177: Space between icon and text

# Icon label - COMPACT
icon_label = QLabel(icon)
icon_label.setStyleSheet("""
    QLabel {
        font-size: 14px;          # ← LINE 183: Icon size
        background: transparent;
        border: none;
    }
""")

# Name label - COMPACT
name_label = QLabel(name)
name_label.setStyleSheet(f"""
    QLabel {{
        color: {color};
        font-size: 10px;          # ← LINE 196: Category name font size
        font-weight: bold;
        background: transparent;
        border: none;
    }}
""")
```

**Change here to adjust:**
- **Category item padding**: Line 176
- **Icon to text spacing**: Line 177
- **Icon size**: Line 183
- **Category name font**: Line 196

---

## 📦 Page Layout Spacing

### Location: `CategorizedActionLibrary.create_category_page()` method (Lines 381-398)

```python
def create_category_page(self, category_info: dict) -> QWidget:
    """Create category page with action cards - COMPACT"""
    page = QWidget()
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(5, 5, 5, 5)     # ← LINE 382: Page margins
    page_layout.setSpacing(5)                      # ← LINE 383: Space between elements

    # Category description - COMPACT
    desc_label = QLabel(category_info.get("description", ""))
    desc_label.setStyleSheet("""
        QLabel {
            color: #666;
            font-size: 10px;      # ← LINE 390: Description font size
            padding: 5px;         # ← LINE 391: Description padding
            background-color: white;
            border-radius: 3px;
            border: 1px solid #E0E0E0;
        }
    """)
```

**Change here to adjust:**
- **Page margins**: Line 382
- **Page element spacing**: Line 383
- **Category description font**: Line 390
- **Category description padding**: Line 391

---

## 🗂️ Grid Layout Spacing

### Location: `CategorizedActionLibrary.create_category_page()` method (Lines 430-434)

```python
# Card container - COMPACT
card_container = QWidget()
card_container.setStyleSheet("background: transparent;")
grid_layout = QGridLayout(card_container)
grid_layout.setSpacing(3)                 # ← LINE 431: Space between cards
grid_layout.setContentsMargins(3, 3, 3, 3)    # ← LINE 432: Grid padding
# Prevent column from stretching cards
grid_layout.setColumnStretch(0, 0)        # ← LINE 434: Column stretch (0 = no stretch)
```

**Change here to adjust:**
- **Space between cards**: Line 431
- **Grid container padding**: Line 432
- **Column stretch behavior**: Line 434

---

## 🔍 Search Bar Sizing

### Location: `CategorizedActionLibrary.setup_ui()` method (Lines 271-288)

```python
# Search bar
self.search_input = QLineEdit()
self.search_input.setPlaceholderText("🔍 Search actions...")
self.search_input.setClearButtonEnabled(True)
self.search_input.setStyleSheet("""
    QLineEdit {
        padding: 8px 12px;        # ← LINE 276: Search bar padding
        border: 2px solid #E0E0E0;
        border-radius: 20px;
        font-size: 12px;          # ← LINE 279: Search bar font size
        background: white;
    }
    QLineEdit:focus {
        border-color: #2196F3;
        background: #F8F9FA;
    }
""")
```

**Change here to adjust:**
- **Search bar padding**: Line 276
- **Search bar font size**: Line 279

---

## 📊 Quick Reference Table

| Component | File Line | Current Value | Purpose |
|-----------|-----------|---------------|---------|
| **Card Height Min** | 51 | 50px | Minimum card height |
| **Card Height Max** | 52 | 62px | Maximum card height |
| **Card Width Max** | 54 | 200px | Maximum card width |
| **Card Spacing** | 58 | 2px | Space between name/desc |
| **Card Padding** | 59 | 4px | Card internal padding |
| **Name Font Size** | 65 | 11px | Action name font |
| **Desc Font Size** | 87 | 8px | Description font |
| **Category List Width** | 315 | 100px | Category list width |
| **Grid Card Spacing** | 431 | 3px | Space between cards |
| **Grid Padding** | 432 | 3px | Grid container padding |
| **Page Margins** | 382 | 5px | Page outer margins |

---

## 🎛️ Common Adjustments

### Make cards bigger:
```python
# Line 51-52
self.setMinimumHeight(70)
self.setMaximumHeight(90)

# Line 54
self.setMaximumWidth(250)

# Line 65, 87
font-size: 12px;  # name
font-size: 9px;   # description
```

### Make everything more spacious:
```python
# Line 59
layout.setContentsMargins(8, 8, 8, 8)

# Line 431
grid_layout.setSpacing(5)

# Line 382
page_layout.setContentsMargins(10, 10, 10, 10)
```

### Make category list wider:
```python
# Line 315
self.category_list.setFixedWidth(150)
```

### Make everything ultra-compact:
```python
# Card dimensions (Lines 51-54)
self.setMinimumHeight(40)
self.setMaximumHeight(50)
self.setMaximumWidth(150)

# All margins to 2px
# All spacing to 1px
# All fonts -1px smaller
```

---

## ⚠️ Important Notes

1. **After changing values**, restart the application to see changes
2. **Card width** is limited by `setMaximumWidth()` on line 54
3. **Text will wrap** if card is too narrow for long names
4. **Minimum readable font sizes**:
   - Name: ~10px
   - Description: ~8px
5. **Touch-friendly minimum height**: ~50px for cards

---

## 🧪 Testing Your Changes

After making changes:
```bash
# 1. Check syntax
python3 -m py_compile categorized_action_library_improved.py

# 2. Run tests
python3 test_new_components.py

# 3. Run application
python3 main.py
```

---

## 📍 File Location Summary

**All changes in ONE file:** `categorized_action_library_improved.py`

**Key sections:**
- **Lines 50-100**: ActionCard dimensions and styling
- **Lines 175-203**: CategoryListItem styling
- **Lines 270-288**: Search bar styling
- **Line 315**: Category list width
- **Lines 380-434**: Page layout and grid spacing

---

**Tip:** Make small changes incrementally and test to find your preferred dimensions!
