# Tools Website

A comprehensive web-based utility tools collection built with FastAPI and modern web technologies.

## 🔧 Features

### Core Tools
- **📅 Calendar Viewer**: Parse and display .cal/.ics calendar files with DataTables integration
- **🔡 String to ASCII Converter**: Convert text to ASCII character codes with tabular output
- **🧩 JSON Editor**: Visual JSON editing with tree and code views using JSONEditor
- **🔍 JSON Compare**: Advanced JSON comparison tool with difference highlighting
- **🎥 Video Downloader**: Download videos from direct URLs (non-YouTube)

### Technical Features
- **🔐 Secure Authentication**: Cookie-based session management
- **📱 Responsive Design**: Works on desktop, tablet, and mobile devices
- **⚡ Fast Performance**: Built with FastAPI for optimal speed
- **🎨 Modern UI**: Clean, intuitive interface with collapsible sections
- **🛡️ Security Focus**: Input validation, file size limits, and secure sessions

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone or create project directory**
   ```bash
   mkdir tools-website
   cd tools-website
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env-example .env
   cp .config-example .config
   # Edit .env with your configuration
   ```

5. **Download third-party libraries**
   ```bash
   # Create directories
   mkdir -p static/vendor/jquery static/vendor/datatables static/vendor/jsoneditor static/lib

   # Download jQuery
   curl -o static/vendor/jquery/jquery-3.7.1.min.js https://code.jquery.com/jquery-3.7.1.min.js

   # Download DataTables
   curl -o static/vendor/datatables/jquery.dataTables.min.css https://cdn.datatables.net/1.13.5/css/jquery.dataTables.min.css
   curl -o static/vendor/datatables/jquery.dataTables.min.js https://cdn.datatables.net/1.13.5/js/jquery.dataTables.min.js

   # Download JSONEditor
   curl -o static/vendor/jsoneditor/jsoneditor.min.css https://unpkg.com/jsoneditor@10.0.3/dist/jsoneditor.min.css
   curl -o static/vendor/jsoneditor/jsoneditor.min.js https://unpkg.com/jsoneditor@10.0.3/dist/jsoneditor.min.js
   ```

6. **Run the application**
   ```bash
   python main.py
   # Or with uvicorn directly:
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

7. **Access the website**
   - Open http://localhost:8000 in your browser
   - Login with demo credentials: admin / password

## 📁 Project Structure

```
tools-website/
├── .env                          # Environment variables (create from .env-example)
├── .config                       # Configuration metadata (create from .config-example)
├── main.py                       # FastAPI application entry point
├── requirements.txt              # Python dependencies
├── README.md                     # This file
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
```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Authentication
AUTH_SECRET_KEY=your-secret-key-here

# Application settings
TOOLS_MAX_FILE_SIZE_MB=50
TOOLS_SESSION_TIMEOUT_HOURS=24
JSON_MAX_SIZE_MB=10

# External APIs
VIDEO_API_TIMEOUT_SEC=30

# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Security Notes
- Change `AUTH_SECRET_KEY` in production
- Set `DEBUG=false` in production
- Use HTTPS in production environments
- Consider implementing more robust authentication for production use

## 🔨 Development

### Adding New Tools

1. **Add HTML section** to `static/tools.html`:
   ```html
   <div class="section">
       <div class="section-header" onclick="toggleSection('new-tool')">
           <span>🔧 New Tool Name</span>
           <span class="section-toggle" id="new-tool-toggle">▶</span>
       </div>
       <div class="section-content" id="new-tool-content">
           <!-- Tool interface -->
       </div>
   </div>
   ```

2. **Implement JavaScript logic** in the same file or `static/utils.js`

3. **Add backend endpoints** in `main.py` if needed

4. **Test thoroughly** across different browsers and devices

### Code Style Guidelines
- Follow PEP 8 for Python code
- Use modern ES6+ JavaScript features
- Implement proper error handling
- Comment complex logic
- Use meaningful variable names

## 🧪 Testing

### Manual Testing Checklist
- [ ] All tools load and function correctly
- [ ] File uploads work with various file types and sizes
- [ ] Authentication flow works (login/logout)
- [ ] Responsive design on different screen sizes
- [ ] Error handling displays appropriate messages
- [ ] No JavaScript console errors

### Browser Compatibility
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=false` in environment
- [ ] Use secure `AUTH_SECRET_KEY`
- [ ] Configure HTTPS/SSL
- [ ] Set up reverse proxy (nginx recommended)
- [ ] Configure proper logging
- [ ] Set up monitoring and health checks
- [ ] Implement backup strategy

### Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py"]
```

## 📚 API Documentation

### Authentication Endpoints
- `GET /login.html` - Login page
- `POST /auth/login` - Authenticate user
- `POST /auth/logout` - Logout user

### Tool Endpoints
- `GET /tools.html` - Main tools interface (requires auth)
- `POST /tools/download_video` - Download video from URL

### Utility Endpoints
- `GET /health` - Health check
- `GET /static/{path}` - Static file serving

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

### Common Issues

**Issue**: Third-party libraries not loading
**Solution**: Ensure all vendor files are downloaded correctly and paths are correct

**Issue**: Authentication not working
**Solution**: Check `AUTH_SECRET_KEY` is set and cookies are enabled

**Issue**: File uploads failing
**Solution**: Check `TOOLS_MAX_FILE_SIZE_MB` setting and server disk space

### Getting Help
- Check the browser console for JavaScript errors
- Review server logs for backend issues
- Ensure all dependencies are installed correctly
- Verify configuration settings in .env file

## 🎯 Roadmap

### Planned Features
- [ ] Database connectivity tool
- [ ] Image processing utilities
- [ ] Text analysis tools
- [ ] API testing interface
- [ ] File conversion utilities
- [ ] Regular expression tester
- [ ] Color palette generator
- [ ] QR code generator/reader

### Technical Improvements
- [ ] Add unit tests
- [ ] Implement API rate limiting
- [ ] Add user management system
- [ ] Improve error logging
- [ ] Add caching for better performance
- [ ] Implement file upload progress indicators