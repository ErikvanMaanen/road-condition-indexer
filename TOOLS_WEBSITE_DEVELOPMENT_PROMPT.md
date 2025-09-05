# Tools Website Development Prompt

## Project Overview

Create a comprehensive web-based tools website that provides a collection of utility tools for developers, analysts, and general users. The website should be a standalone application focused exclusively on providing useful tools without any other application functionality.

## Technology Stack

### Backend
- **Framework**: Python FastAPI (lightweight, fast, modern)
- **Server**: Uvicorn ASGI server with hot reload support
- **Authentication**: Cookie-based session management with MD5 hashing
- **HTTP Client**: Requests library for external API calls

### Frontend
- **Core**: Pure HTML5, CSS3, and JavaScript (ES6+)
- **UI Framework**: Custom responsive design with collapsible sections
- **Data Visualization**: jQuery DataTables for tabular data
- **JSON Handling**: JSONEditor library for tree/code view editing
- **Icons**: Unicode emoji icons for visual appeal

### Dependencies
- **jQuery**: 3.7.1+ for DOM manipulation and AJAX
- **DataTables**: 1.13.5+ for table functionality
- **JSONEditor**: 10.0.3+ for JSON editing capabilities
- **Custom Libraries**: Simple JSON diff implementation

## Project Structure

```
tools-website/
├── .env                          # Environment variables (secrets)
├── .config                       # Configuration metadata
├── main.py                       # FastAPI application entry point
├── requirements.txt              # Python dependencies
├── static/                       # Static web assets
│   ├── tools.html               # Main tools interface
│   ├── login.html               # Authentication interface
│   ├── utils.js                 # Common JavaScript utilities
│   ├── favicon.ico              # Website icon
│   ├── logo.png                 # Branding logo
│   ├── lib/                     # Custom libraries
│   │   ├── simple-json-diff.js  # JSON comparison utility
│   │   ├── simple-json-diff.css # JSON diff styling
│   │   └── README.md            # Library documentation
│   └── vendor/                  # Third-party libraries
│       ├── jquery/              # jQuery library files
│       ├── datatables/          # DataTables plugin files
│       └── jsoneditor/          # JSON Editor component files
└── README.md                    # Project documentation
```

## Configuration Files

### .env File
```env
# Authentication
AUTH_SECRET_KEY=your-secret-key-here

# Application settings
TOOLS_MAX_FILE_SIZE_MB=50
TOOLS_SESSION_TIMEOUT_HOURS=24

# External APIs (optional)
VIDEO_API_TIMEOUT_SEC=30
JSON_MAX_SIZE_MB=10

# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### .config File
```ini
[SECTION Authentication]
META Purpose=Session management and user access control
SECRET AUTH_SECRET_KEY=REPLACE_WITH_SECURE_RANDOM_STRING
VAR    SESSION_TIMEOUT_HOURS=24
REQUIRE AUTH_SECRET_KEY secret
REQUIRE SESSION_TIMEOUT_HOURS public

[SECTION Application]
META Purpose=Tool-specific limits and configurations
VAR  TOOLS_MAX_FILE_SIZE_MB=50
VAR  JSON_MAX_SIZE_MB=10
VAR  VIDEO_API_TIMEOUT_SEC=30
REQUIRE TOOLS_MAX_FILE_SIZE_MB public
REQUIRE JSON_MAX_SIZE_MB public
REQUIRE VIDEO_API_TIMEOUT_SEC public

[SECTION Server]
META Purpose=Server runtime configuration
VAR  HOST=0.0.0.0
VAR  PORT=8000
VAR  DEBUG=true
REQUIRE HOST public
REQUIRE PORT public
REQUIRE DEBUG public
```

## Core Tools Implementation

### 1. Calendar Viewer Tool
- **Purpose**: Parse and display .cal/.ics calendar files
- **Features**:
  - Drag & drop file upload
  - Multiple file support
  - DataTables integration for sorting/filtering
  - Date formatting with timezone awareness
- **Implementation**: Pure JavaScript ICS parser with event extraction

### 2. String to ASCII Converter
- **Purpose**: Convert text to ASCII character codes
- **Features**:
  - Real-time conversion
  - Character-by-character breakdown
  - Special character handling (spaces, line breaks)
  - Tabular output with DataTables

### 3. JSON Editor
- **Purpose**: Visual JSON editing with tree and code views
- **Features**:
  - JSONEditor library integration
  - File upload and drag & drop
  - Download edited JSON
  - Error validation and handling
  - Collapsible tree structure

### 4. JSON Comparison Tool
- **Purpose**: Compare two JSON objects for differences and similarities
- **Features**:
  - Side-by-side comparison interface
  - Custom diff algorithm implementation
  - Visual highlighting (added/removed/modified/unchanged)
  - Expandable/collapsible diff sections
  - Toggle visibility for different change types

### 5. Video Downloader
- **Purpose**: Download videos from direct URLs (non-YouTube)
- **Features**:
  - URL validation and processing
  - Stream-based downloading
  - Content-type detection
  - Progress indication
  - File naming based on content headers

## User Interface Design

### Layout Principles
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Collapsible Sections**: Each tool in expandable section with emoji icons
- **Consistent Styling**: Unified color scheme and typography
- **Accessibility**: Proper ARIA labels and keyboard navigation

### Color Scheme
- **Primary**: #007cba (blue for links and highlights)
- **Success**: #28a745 (green for added/success states)
- **Warning**: #ffc107 (yellow for modified/warning states)
- **Danger**: #dc3545 (red for removed/error states)
- **Light**: #f8f9fa (backgrounds and subtle elements)

### Typography
- **Body Text**: Arial, sans-serif
- **Code/Data**: 'Courier New', monospace
- **Headings**: Bold Arial with consistent sizing

## Backend API Design

### Authentication Endpoints
```python
@app.get("/login.html")
def login_page():
    """Serve login interface"""

@app.post("/auth/login")
def authenticate(credentials: LoginRequest):
    """Process login credentials"""

@app.post("/auth/logout")
def logout():
    """Clear authentication session"""
```

### Tool Endpoints
```python
@app.get("/tools.html")
def tools_page(request: Request):
    """Serve main tools interface (requires auth)"""

@app.post("/tools/download_video")
def download_video(request: VideoDownloadRequest):
    """Download video from URL"""

@app.get("/static/{path:path}")
def static_files(path: str):
    """Serve static assets"""
```

## Security Considerations

### Authentication
- Cookie-based session management
- MD5 hash-based session tokens
- Session timeout enforcement
- Login required for all tool access

### File Handling
- Size limits for uploaded files
- Extension validation for security
- Temporary file cleanup
- No server-side file storage

### External Requests
- Timeout limits for video downloads
- URL validation and sanitization
- No YouTube support (avoid copyright issues)
- Request size limitations

## Development Setup Instructions

### 1. Environment Setup
```bash
# Create project directory
mkdir tools-website
cd tools-website

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn requests python-dotenv
```

### 2. Configuration Setup
```bash
# Copy configuration templates
cp .env-example .env
cp .config-example .config

# Edit .env with your secrets
# Set AUTH_SECRET_KEY to a secure random string
```

### 3. Download Third-Party Libraries
```bash
# Create vendor directories
mkdir -p static/vendor/jquery static/vendor/datatables static/vendor/jsoneditor

# Download jQuery
curl -o static/vendor/jquery/jquery-3.7.1.min.js \
  https://code.jquery.com/jquery-3.7.1.min.js

# Download DataTables
curl -o static/vendor/datatables/jquery.dataTables.min.css \
  https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css
curl -o static/vendor/datatables/jquery.dataTables.min.js \
  https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js

# Download JSONEditor
curl -o static/vendor/jsoneditor/jsoneditor.min.css \
  https://unpkg.com/jsoneditor@10.0.3/dist/jsoneditor.min.css
curl -o static/vendor/jsoneditor/jsoneditor.min.js \
  https://unpkg.com/jsoneditor@10.0.3/dist/jsoneditor.min.js
```

### 4. Run Development Server
```bash
# Start with hot reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Access at http://localhost:8000
```

## Implementation Guidelines

### JavaScript Best Practices
- Use modern ES6+ features (const/let, arrow functions, template literals)
- Implement proper error handling with try/catch blocks
- Use async/await for asynchronous operations
- Avoid global variables, use proper scoping
- Comment complex algorithms and business logic

### CSS Organization
- Use CSS custom properties for theming
- Implement responsive design with CSS Grid and Flexbox
- Follow BEM naming convention for CSS classes
- Minimize use of !important declarations
- Use relative units (rem, em, %) for scalability

### Python Code Standards
- Follow PEP 8 style guidelines
- Use type hints for function parameters and returns
- Implement proper exception handling
- Use dependency injection for testability
- Document functions with docstrings

### File Organization
- Separate concerns (HTML structure, CSS styling, JS behavior)
- Use absolute paths for static asset references
- Organize third-party libraries in vendor/ directory
- Keep custom implementations in lib/ directory
- Maintain clear directory structure

## Testing Strategy

### Frontend Testing
- Manual testing across different browsers
- Responsive design testing on various screen sizes
- File upload testing with different file types and sizes
- JavaScript error monitoring in browser console

### Backend Testing
- API endpoint testing with different request types
- Authentication flow testing
- File upload size limit testing
- Error handling validation

### Integration Testing
- End-to-end tool functionality testing
- Cross-browser compatibility verification
- Performance testing with large files
- Security testing for authentication bypass

## Deployment Considerations

### Production Setup
- Set DEBUG=false in production environment
- Use environment variables for all secrets
- Implement proper logging and monitoring
- Set up reverse proxy (nginx) for static file serving
- Configure SSL/TLS certificates for HTTPS

### Performance Optimization
- Minimize JavaScript and CSS files
- Implement proper caching headers for static assets
- Use CDN for third-party libraries (with CORS fallback)
- Optimize images and icons for web delivery

### Monitoring and Maintenance
- Implement application logging for troubleshooting
- Set up health check endpoints
- Monitor resource usage and performance metrics
- Regular security updates for dependencies

## Extensibility Framework

### Adding New Tools
1. Add new section to tools.html with collapsible interface
2. Implement tool logic in JavaScript with proper error handling
3. Add any required backend endpoints in main.py
4. Update navigation and documentation
5. Test thoroughly across different browsers and devices

### Tool Interface Template
```html
<!-- New Tool Section -->
<div class="section">
    <div class="section-header" onclick="toggleSection('new-tool')">
        <span>🔧 New Tool Name</span>
        <span class="section-toggle" id="new-tool-toggle">▶</span>
    </div>
    <div class="section-content" id="new-tool-content">
        <!-- Tool interface HTML -->
        <!-- Input fields, buttons, result areas -->
    </div>
</div>
```

### JavaScript Tool Template
```javascript
// New Tool Implementation
const newToolElements = {
    input: document.getElementById('new-tool-input'),
    button: document.getElementById('new-tool-button'),
    result: document.getElementById('new-tool-result')
};

newToolElements.button.addEventListener('click', async () => {
    try {
        // Tool logic implementation
        const input = newToolElements.input.value.trim();
        if (!input) {
            alert('Please provide input');
            return;
        }
        
        // Process input and display result
        const result = processInput(input);
        newToolElements.result.innerHTML = formatResult(result);
    } catch (error) {
        console.error('New tool error:', error);
        alert('Error: ' + error.message);
    }
});
```

## Success Criteria

### Functional Requirements
- All five core tools working correctly
- Responsive design across devices
- File upload and download capabilities
- Authentication system protecting tool access
- Error handling and user feedback

### Performance Requirements
- Page load time under 3 seconds on standard connection
- Tool operations complete within 10 seconds for typical use cases
- File uploads support up to 50MB without timeout
- Memory usage remains stable during extended use

### Usability Requirements
- Intuitive interface requiring no training
- Clear visual feedback for all user actions
- Accessible keyboard navigation
- Help text and error messages in plain language

### Technical Requirements
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- Mobile-responsive design
- Secure authentication implementation
- Clean, maintainable code structure
- Proper error logging for debugging

This development prompt provides a complete foundation for creating a professional, feature-rich tools website that can be extended and maintained over time.