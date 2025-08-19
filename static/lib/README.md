# Third-Party Libraries Setup

This directory contains custom implementations and local libraries to avoid Cross-Origin Read Blocking (CORB) issues when loading from external CDNs.

## Directory Structure

```
static/
├── lib/                     # Custom implementations
│   ├── simple-json-diff.js  # Custom JSON diff implementation
│   ├── simple-json-diff.css # Custom JSON diff styles
│   └── README.md            # This file
└── vendor/                  # Third-party libraries
    ├── jquery/              # jQuery library
    ├── datatables/          # DataTables plugin
    └── jsoneditor/          # JSON Editor component
```

## Required Files

The following files need to be downloaded to the `static/vendor/` subdirectories for the tools.html page to work properly:

### jQuery (`static/vendor/jquery/`)
- `jquery-3.7.1.min.js` - from https://code.jquery.com/jquery-3.7.1.min.js

### DataTables (`static/vendor/datatables/`)
- `jquery.dataTables.min.css` - from https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css  
- `jquery.dataTables.min.js` - from https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js

### JSON Editor (`static/vendor/jsoneditor/`)
- `jsoneditor.min.css` - from https://unpkg.com/jsoneditor@9.10.5/dist/jsoneditor.min.css
- `jsoneditor.min.js` - from https://unpkg.com/jsoneditor@9.10.5/dist/jsoneditor.min.js

### JSON Diff (Custom Implementation - `static/lib/`)
- `simple-json-diff.css` - Custom styles for JSON diff display
- `simple-json-diff.js` - Custom JSON diff implementation (replaces jsondiffpatch)

## Download Script (PowerShell)

To re-download all external libraries, run this PowerShell script from the project root:

```powershell
# Create vendor directory structure
New-Item -ItemType Directory -Force -Path "static\vendor\jquery"
New-Item -ItemType Directory -Force -Path "static\vendor\datatables"
New-Item -ItemType Directory -Force -Path "static\vendor\jsoneditor"

# Download jQuery
Invoke-WebRequest -Uri "https://code.jquery.com/jquery-3.7.1.min.js" -OutFile "static\vendor\jquery\jquery-3.7.1.min.js"

# Download DataTables
Invoke-WebRequest -Uri "https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css" -OutFile "static\vendor\datatables\jquery.dataTables.min.css"
Invoke-WebRequest -Uri "https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js" -OutFile "static\vendor\datatables\jquery.dataTables.min.js"

# Download JSON Editor
Invoke-WebRequest -Uri "https://unpkg.com/jsoneditor@9.10.5/dist/jsoneditor.min.css" -OutFile "static\vendor\jsoneditor\jsoneditor.min.css"
Invoke-WebRequest -Uri "https://unpkg.com/jsoneditor@9.10.5/dist/jsoneditor.min.js" -OutFile "static\vendor\jsoneditor\jsoneditor.min.js"

Write-Host "All third-party libraries downloaded successfully!"
```

## Why Local Libraries?

External CDN libraries can trigger Cross-Origin Read Blocking (CORB) in certain browser configurations, causing the tools page to fail loading essential functionality. By hosting these libraries locally, we ensure:

1. No CORB errors
2. Faster loading (no external network requests)  
3. Consistent functionality even when offline
4. Better control over library versions

The custom `simple-json-diff.js` implementation provides the same API as jsondiffpatch but with a simpler, more reliable codebase that doesn't require external dependencies.

## Path Configuration

All static files are served via FastAPI at `/static/` URLs:
- CSS files: `/static/vendor/[vendor]/[file].css` and `/static/lib/[file].css`
- JS files: `/static/vendor/[vendor]/[file].js` and `/static/lib/[file].js`

This ensures proper loading when the tools.html page is accessed via the web server.
