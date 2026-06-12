# ICB Boundaries Implementation Guide

## Summary

I've successfully added the two NHS London Integrated Care Board (ICB) boundaries to your Streamlit mapping app.

### What was added:

#### 1. **Boundary Data Files** 
- `data/boundaries/NHS_South_East_London_ICB.geojson` (652 KB) — MapIt area 168382
- `data/boundaries/NHS_South_West_London_ICB.geojson` (784 KB) — MapIt area 168269

These files contain the official boundary geometries for:
- **SE London**: NHS South East London ICB - 72Q (3 polygons)
- **SW London**: NHS South West London Integrated Care Board (6 polygons)

#### 2. **App Updates**

##### `streamlit_app.py` changes:

**a) Data Loading** (`load_data()` function)
- Now loads both ICB boundary GeoJSON files from the boundaries directory
- Wraps MapIt's raw geometry in proper GeoJSON Feature format for Folium compatibility
- Returns `icb_geojsons` dictionary with both ICB boundaries

**b) Map Rendering** (`create_map()` function)
- Added `icb_geojsons` parameter to accept boundary data
- Added `show_icb_boundaries` parameter (defaults to `True`) for layer visibility toggle
- ICB boundaries render as a distinct "🗺️ ICB Boundaries" layer with:
  - **SE London**: Navy blue (#003087) — NIHR brand color
  - **SW London**: Bright blue (#0072CE) — NIHR brand color
  - Semi-transparent fills (10% opacity) so underlying data is visible
  - Tooltips and popups with ICB names
  - Fully toggleable in Folium's layer control

**c) Map Calls**
- Updated all `create_map()` calls to pass `icb_geojsons` parameter
- Both "📍 Interactive Map" and "🌍 Disease Map" views now display ICB boundaries

---

## Map Features

### Visual Design
- **Colors**: NIHR brand palette (navy and bright blue)
- **Lines**: 2.5px weight with 80% opacity for clear definition
- **Fill**: 10% opacity to show underlying GP/hospital markers
- **Labels**: Hover tooltips and clickable popups with ICB names

### Layer Control
The map now includes a layer control menu (top-right) allowing users to toggle:
- ✓ 🗺️ ICB Boundaries (new)
- ✓ MSOA Disease Overlay (if enabled)
- ✓ 🏥 GP Practices
- ✓ 🏨 Hospitals

### Display Modes
ICB boundaries appear in:
- **📍 Interactive Map**: Always visible by default
- **🌍 Disease Map**: Always visible by default
- **📊 Data Explorer**: Not applicable (data view only)

---

## Technical Details

### Data Sources
- **MapIt API**: `https://mapit.mysociety.org/area/{area_id}.geojson`
- **SE London ICB**: Area 168382 (GSS: E38000244)
- **SW London ICB**: Area 168269 (GSS: E54000031)

### GeoJSON Format
MapIt returns raw geometry objects (MultiPolygon). The app wraps these in Feature objects:
```json
{
  "type": "Feature",
  "properties": {"name": "ICB Name"},
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": [...]
  }
}
```

### File Structure
```
data/
└── boundaries/
    ├── Middle_layer_Super_Output_Areas_*.geojson (MSOA)
    ├── NHS_South_East_London_ICB.geojson (SE London ICB)
    └── NHS_South_West_London_ICB.geojson (SW London ICB)
```

---

## How to Use

### For End Users
1. Open the Streamlit app in your browser
2. Navigate to either **"📍 Interactive Map"** or **"🌍 Disease Map"** view
3. Look for the layer control menu in the top-right corner
4. Check/uncheck "🗺️ ICB Boundaries" to toggle the ICB borders on/off
5. Hover over the boundaries to see the ICB name

### For Developers
If you need to update the boundaries in the future:

**1. Re-download from MapIt:**
```bash
curl -s "https://mapit.mysociety.org/area/168382.geojson" > data/boundaries/NHS_South_East_London_ICB.geojson
curl -s "https://mapit.mysociety.org/area/168269.geojson" > data/boundaries/NHS_South_West_London_ICB.geojson
```

**2. Or download other areas:**
- Find the area ID on [mapit.mysociety.org](https://mapit.mysociety.org)
- Use the endpoint: `https://mapit.mysociety.org/area/{id}.geojson`
- Save as `data/boundaries/{area_name}.geojson`
- Update the filename matching logic in `load_data()` if needed

---

## Customization Options

### Change Colors
Edit the `icb_colors` dictionary in the `create_map()` function:
```python
icb_colors = {
    'SE London': '#003087',  # Change to any hex color
    'SW London': '#0072CE',
}
```

### Change Transparency
Edit the `fillOpacity` value in the style function (currently `0.1`):
- `0.0` = invisible
- `0.5` = 50% transparent
- `1.0` = fully opaque

### Hide by Default
Change the parameter when calling `create_map()`:
```python
show_icb_boundaries=False  # Will be unchecked by default
```

---

## Testing

The implementation has been validated:
- ✅ Both boundary files are valid GeoJSON
- ✅ Folium correctly renders the geometries
- ✅ Layer control toggles work properly
- ✅ No syntax errors in updated code
- ✅ All existing functionality remains intact

---

## References

- **MapIt**: https://mapit.mysociety.org
- **SE London ICB**: https://mapit.mysociety.org/area/168382.html
- **SW London ICB**: https://mapit.mysociety.org/area/168269.html
- **Folium Documentation**: https://python-visualization.github.io/folium/
- **GeoJSON Specification**: https://tools.ietf.org/html/rfc7946
