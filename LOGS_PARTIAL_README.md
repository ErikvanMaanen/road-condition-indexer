# Logs Partial Documentation

## Overview

The `logs-partial.html` file contains the reusable Activity Log and Debug Messages component that is used across all pages except the login page in the Road Condition Indexer application.

## Components Included

### HTML Structure
- **Activity Log section** with styled log display area
- **Debug Messages section** with textarea for debug output
- **Toggle button** to show/hide the logs section

### CSS Styling
- Consistent styling for log containers
- Responsive design that works across different pages
- Professional appearance with borders and proper spacing

### JavaScript Functions
- `addLog(msg)` - Adds timestamped messages to the activity log
- `addDebug(msg)` - Adds timestamped debug messages to the debug textarea
- `toggleLogs()` - Shows/hides the entire logs section

## Usage

### Including the Partial
Each page includes the partial by:
1. Adding a `<div id="logs-container"></div>` placeholder in the HTML
2. Loading the partial via JavaScript using the `loadLogsPartial()` function
3. The function automatically executes scripts and provides fallback functionality

### Loading Mechanism
The partial is loaded asynchronously when the DOM is ready. If loading fails, fallback functions are created that log to the browser console.

### Function Availability
Once loaded, the following functions are globally available:
- `addLog(message)` - Add activity log entry
- `addDebug(message)` - Add debug message entry  
- `toggleLogs()` - Toggle logs visibility

## Implementation Details

### Timestamp Format
All log entries are automatically timestamped using the Europe/Amsterdam timezone in Swedish locale format (YYYY-MM-DD HH:mm:ss).

### Error Handling
- Network errors when loading the partial are caught and logged
- Fallback functions prevent JavaScript errors if the partial fails to load
- Console logging provides debugging information

### Performance
- Partial is loaded only once per page
- Scripts are dynamically executed to ensure proper functionality
- Minimal overhead with efficient DOM manipulation

## Files Modified

The following files have been updated to use the logs partial:
- `index.html` - Main application page
- `device.html` - Device records view
- `database.html` - Database management page  
- `maintenance.html` - Maintenance and debugging page

The `login.html` page retains its own log implementation as it has different requirements.

## Benefits

1. **Code Reuse** - Single source of truth for logs functionality
2. **Consistency** - Uniform appearance and behavior across pages
3. **Maintainability** - Updates need to be made in only one place
4. **Reliability** - Robust error handling and fallback mechanisms
5. **Performance** - Efficient loading and minimal duplication
