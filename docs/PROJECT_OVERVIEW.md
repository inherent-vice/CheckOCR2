# CheckOCR2 Project Overview

## Project Description
CheckOCR2 is a comprehensive OCR (Optical Character Recognition) desktop application built with Python and Tkinter. The application specializes in automated data extraction from screen captures, with a focus on financial data processing including stock codes, company names, dates, and interest rates.

## Key Features
- **Screen Capture & OCR**: Automated screen capture with region selection and OCR processing
- **Excel Integration**: Import/export Excel files with comprehensive data management
- **Multi-threading**: Asynchronous processing with worker threads for non-blocking UI
- **Theme Management**: Modern UI with customizable themes and dark/light mode support
- **Advanced Settings**: Configurable OCR parameters, timing controls, and processing options
- **Data Validation**: Built-in validation for extracted data with error handling
- **Preset Management**: Save and load processing presets for different use cases
- **Real-time Progress**: Live progress tracking with detailed status updates

## Core Components

### Main Application (`CheckCaptureOCRApp`)
- Central GUI application class inheriting from `tkinter.Tk`
- Manages all UI components and coordinates between different modules
- Handles user interactions and application lifecycle

### Logging System
- Comprehensive logging with configurable levels (DEBUG, INFO, WARNING, ERROR)
- File-based logging with rotation and console output
- Thread-safe logging for multi-threaded operations

### Settings Management (`SettingsManager`)
- Persistent configuration storage using JSON files
- Advanced settings for OCR parameters, UI preferences, and processing options
- Preset management for saving/loading different configurations

### Theme Management (`ThemeManager`)
- Modern UI theming system with multiple color schemes
- Dynamic theme switching without application restart
- Widget registration system for consistent styling### Work Controller (`WorkController`)
- Controls the execution flow of OCR processing tasks
- Thread-safe start/stop mechanisms with proper cleanup
- Status tracking and progress reporting

### Area Visualization System
- Interactive overlay windows for region selection
- Visual feedback for capture areas with customizable colors
- Drag-and-drop interface for area positioning

### Data Management (`DataManager`)
- Excel data import/export functionality
- In-memory data structure management for processing results
- Data validation and transformation utilities
- Grid synchronization with UI components

### OCR Workflow Management
- Automated capture and processing pipeline
- Error handling and retry mechanisms
- Progress tracking and status reporting
- Integration with external OCR services/libraries

## Technical Architecture

### Multi-threading Design
- Main UI thread for user interface responsiveness
- Worker threads for OCR processing and file operations
- Message queue system for thread-safe communication
- Proper thread synchronization and cleanup

### Configuration Management
- JSON-based configuration files for settings persistence
- Hierarchical settings structure (basic/advanced)
- Default value handling and validation
- Migration support for configuration updates

### Error Handling Strategy
- Comprehensive exception handling throughout the application
- User-friendly error messages with technical details in logs
- Graceful degradation when components fail
- Recovery mechanisms for common error scenarios## File Structure
```
CheckOCR2/
├── Check_Capture_Excel_V6.1_배포.py    # Main application file
├── DEPLOYMENT_GUIDE.md                 # Deployment instructions
├── docs/                               # Documentation directory
│   ├── PROJECT_OVERVIEW.md            # This file
│   └── IMPROVEMENT_SUGGESTIONS.md     # Improvement recommendations
└── [Additional files and dependencies]
```

## Dependencies
- **tkinter**: GUI framework (built-in with Python)
- **threading**: Multi-threading support (built-in)
- **json**: Configuration file handling (built-in)
- **logging**: Comprehensive logging system (built-in)
- **datetime**: Date/time operations (built-in)
- **pathlib**: Modern path handling (built-in)
- **PIL/Pillow**: Image processing (external)
- **openpyxl**: Excel file operations (external)
- **Additional OCR libraries**: As specified in requirements

## Target Use Cases
1. **Financial Data Extraction**: Automated extraction of stock prices, rates, and financial metrics
2. **Document Processing**: Batch processing of documents with structured data
3. **Data Entry Automation**: Reducing manual data entry through OCR automation
4. **Quality Assurance**: Validation and verification of extracted data
5. **Report Generation**: Automated generation of reports from processed data

## Performance Characteristics
- **Processing Speed**: Optimized for batch processing with configurable timing
- **Memory Usage**: Efficient memory management with data streaming capabilities
- **Scalability**: Handles large datasets through chunked processing
- **Reliability**: Robust error handling and recovery mechanisms

## Security Considerations
- **Data Privacy**: Local processing without external data transmission
- **File Access**: Controlled file system access with validation
- **Configuration Security**: Secure storage of sensitive settings
- **Input Validation**: Comprehensive validation of user inputs and file contents