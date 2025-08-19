# Static Files Guidelines

This document provides essential guidelines for handling static files in the Road Condition Indexer application to prevent CORB errors, loading issues, and maintain consistency.

## 📁 Directory Structure

```
static/
├── lib/                          # Custom implementations & local libraries
│   ├── simple-json-diff.css      # Custom JSON diff styles
│   ├── simple-json-diff.js       # Custom JSON diff implementation
│   └── README.md                 # Library setup documentation
├── vendor/                       # Third-party libraries (organized by vendor)
│   ├── jquery/
│   │   └── jquery-3.7.1.min.js
│   ├── datatables/
│   │   ├── jquery.dataTables.min.css
│   │   └── jquery.dataTables.min.js
│   └── jsoneditor/
│       ├── jsoneditor.min.css
│       └── jsoneditor.min.js
├── *.html                        # HTML pages
├── *.js                          # Application JavaScript files (utils.js, map-components.js)
├── *.css                         # Application stylesheets (leaflet.css)
├── *.png, *.ico                  # Images and icons
└── README.md                     # Static files documentation
```

## 🌐 URL Patterns and File References

### ✅ CORRECT: Use Absolute Paths for All Static Resources

**Always use absolute paths starting with `/static/`:**

```html
<!-- CSS Files -->
<link rel="stylesheet" href="/static/vendor/datatables/jquery.dataTables.min.css">
<link rel="stylesheet" href="/static/lib/simple-json-diff.css">

<!-- JavaScript Files -->
<script src="/static/vendor/jquery/jquery-3.7.1.min.js"></script>
<script src="/static/utils.js"></script>

<!-- Images -->
<img src="/static/logo.png" alt="Logo">
<link rel="icon" type="image/x-icon" href="/static/favicon.ico">
```

### ❌ INCORRECT: Avoid Relative Paths

**Never use relative paths:**

```html
<!-- WRONG - These cause loading issues -->
<link rel="stylesheet" href="vendor/datatables/jquery.dataTables.min.css">
<script src="utils.js"></script>
<img src="logo.png" alt="Logo">
```

### 🚫 AVOID: External CDN Links

**Avoid external CDNs to prevent CORB issues:**

```html
<!-- AVOID - These can cause CORB errors -->
<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css">
```

## 📝 When Adding New Features

### Adding Third-Party Libraries

1. **Download to appropriate vendor folder:**
   ```bash
   # Create vendor subdirectory
   New-Item -ItemType Directory -Force -Path "static\vendor\[library-name]"
   
   # Download files
   Invoke-WebRequest -Uri "[library-url]" -OutFile "static\vendor\[library-name]\[file-name]"
   ```

2. **Update HTML references with absolute paths:**
   ```html
   <link rel="stylesheet" href="/static/vendor/[library-name]/[file.css]">
   <script src="/static/vendor/[library-name]/[file.js]"></script>
   ```

3. **Update .gitignore if needed:**
   ```gitignore
   static/vendor/
   !static/vendor/.gitkeep
   !static/vendor/README.md
   ```

### Adding Custom Libraries/Components

1. **Place in `static/lib/` directory:**
   ```
   static/lib/my-custom-component.js
   static/lib/my-custom-component.css
   ```

2. **Reference with absolute paths:**
   ```html
   <link rel="stylesheet" href="/static/lib/my-custom-component.css">
   <script src="/static/lib/my-custom-component.js"></script>
   ```

### Adding Application Assets

1. **Place directly in `static/` directory:**
   ```
   static/my-app-script.js
   static/my-app-styles.css
   static/my-image.png
   ```

2. **Reference with absolute paths:**
   ```html
   <link rel="stylesheet" href="/static/my-app-styles.css">
   <script src="/static/my-app-script.js"></script>
   <img src="/static/my-image.png" alt="Description">
   ```

## ⚙️ FastAPI Configuration

The application serves static files via FastAPI configuration:

```python
# In main.py
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
```

This configuration:
- Serves all files from the `static/` directory
- Makes them available at `/static/` URLs
- Handles MIME types automatically
- Supports nested directory structures

## 🧪 Testing Static Files

### Before Committing Changes

1. **Run verification script:**
   ```powershell
   .\verify-vendor-structure.ps1
   ```

2. **Test static file accessibility:**
   ```powershell
   .\test-static-files.ps1
   ```

3. **Manual testing:**
   - Start the development server
   - Open browser developer tools
   - Check for 404 errors in Network tab
   - Verify all CSS and JS files load correctly

### Quick Test URLs

When server is running on localhost:8000:

- CSS: `http://localhost:8000/static/vendor/datatables/jquery.dataTables.min.css`
- JS: `http://localhost:8000/static/vendor/jquery/jquery-3.7.1.min.js`
- Custom: `http://localhost:8000/static/lib/simple-json-diff.css`
- App files: `http://localhost:8000/static/utils.js`

## 🔧 Common Issues and Solutions

### Issue: CSS/JS Files Not Loading

**Symptoms:**
- Missing styles
- JavaScript functionality broken
- 404 errors in browser console

**Solutions:**
1. Check file paths use absolute URLs (`/static/...`)
2. Verify files exist in correct directories
3. Ensure server is serving static files correctly
4. Clear browser cache

### Issue: CORB Errors

**Symptoms:**
- "Response was blocked by CORB" messages
- External resources failing to load

**Solutions:**
1. Download external libraries locally
2. Place in appropriate `vendor/` subdirectory
3. Update HTML references to local paths
4. Remove external CDN references

### Issue: Development vs Production Differences

**Solutions:**
1. Always use absolute paths (`/static/...`)
2. Test with production-like server setup
3. Avoid hard-coded hostnames or ports
4. Use environment-agnostic URL patterns

## 📋 Checklist for New Features

When adding features that require static files:

- [ ] Use absolute paths for all static resources (`/static/...`)
- [ ] Place third-party libraries in `static/vendor/[vendor-name]/`
- [ ] Place custom libraries in `static/lib/`
- [ ] Place application files directly in `static/`
- [ ] Update documentation if adding new vendor dependencies
- [ ] Test locally with development server
- [ ] Run verification scripts before committing
- [ ] Update `.gitignore` if excluding downloaded files
- [ ] Document any new setup requirements

## 🔄 Migration from Relative to Absolute Paths

If you find existing files using relative paths:

1. **Find all instances:**
   ```powershell
   # Search for relative references
   Select-String -Path "static\*.html" -Pattern 'src="[^/]' -AllMatches
   Select-String -Path "static\*.html" -Pattern 'href="[^/]' -AllMatches
   ```

2. **Update to absolute paths:**
   ```html
   <!-- Change this -->
   <script src="utils.js"></script>
   
   <!-- To this -->
   <script src="/static/utils.js"></script>
   ```

3. **Test thoroughly after changes**

## 🎯 Best Practices Summary

1. **Always use absolute paths** for static resources
2. **Organize by purpose**: `vendor/` for third-party, `lib/` for custom, root for application files
3. **Avoid external CDNs** to prevent CORB issues
4. **Test locally** before deploying
5. **Document dependencies** in README files
6. **Use verification scripts** to catch issues early
7. **Keep consistent** URL patterns across all HTML files

Following these guidelines will prevent static file loading issues and maintain consistency across the application.
