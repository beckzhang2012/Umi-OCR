# Umi-OCR Jupyter Notebook Examples

This directory contains Jupyter notebook examples demonstrating how to use Umi-OCR's HTTP API from Python.

## Overview

These notebooks show how to integrate Umi-OCR's powerful OCR and QR code capabilities into your Python/Jupyter workflows. Perfect for data scientists, researchers, and developers who want to add OCR functionality to their projects.

## Prerequisites

1. **Umi-OCR must be running** on your system
2. **HTTP service must be enabled** in Umi-OCR (enabled by default)
   - Go to Global Settings → Services
   - Ensure HTTP service is enabled
   - Default port is `1224` (localhost only)

## Installation

Install the required Python packages:

```bash
pip install requests pillow pandas tqdm jupyter
```

For optional visualization features:

```bash
pip install ipywidgets matplotlib
```

## Notebooks

### 1. Basic OCR Usage (`01_basic_ocr_usage.ipynb`)

**Learn the fundamentals:**
- Connect to Umi-OCR's HTTP API
- Query available OCR options
- Perform OCR on images
- Use custom OCR parameters
- Work with PIL images
- Handle errors properly

**Best for:** Getting started with Umi-OCR's API

### 2. Batch Processing (`02_batch_processing.ipynb`)

**Process multiple images efficiently:**
- Find images in directories
- Batch OCR processing with progress tracking
- Export results to multiple formats (JSON, CSV, TXT)
- Parallel processing for large batches
- View results in pandas DataFrame

**Best for:** Processing large collections of images, document digitization

### 3. QR Code Operations (`03_qrcode_operations.ipynb`)

**Work with QR codes and barcodes:**
- Read/scan QR codes and barcodes from images
- Generate QR code images from text
- Detect multiple codes in one image
- Batch QR code generation
- Create practical QR code cards

**Best for:** QR code generation, barcode scanning, inventory management

## Quick Start

1. **Start Umi-OCR**
   - Launch Umi-OCR application
   - Ensure HTTP service is enabled (check Global Settings)

2. **Launch Jupyter**
   ```bash
   jupyter notebook
   ```

3. **Open a notebook**
   - Navigate to the `examples/jupyter/` directory
   - Open `01_basic_ocr_usage.ipynb` to start

4. **Run the cells**
   - Execute cells sequentially (Shift+Enter)
   - Modify examples to fit your needs

## Configuration

By default, the notebooks connect to Umi-OCR at:
- Host: `127.0.0.1` (localhost)
- Port: `1224`

If you've changed these settings in Umi-OCR, update the configuration cells in each notebook:

```python
UMI_OCR_HOST = "127.0.0.1"
UMI_OCR_PORT = 1224
BASE_URL = f"http://{UMI_OCR_HOST}:{UMI_OCR_PORT}"
```

## API Response Codes

Understanding response codes helps with error handling:

- `100`: Success - OCR/operation completed successfully
- `101`: No text/code detected in image
- `200`: Parameter error - check your request parameters
- Other codes: Error occurred - check the `data` field for details

## Common Use Cases

### Document Processing
Use batch processing to digitize documents, receipts, or scanned pages.

### Data Extraction
Extract text from screenshots, images, or PDFs for analysis.

### QR Code Management
Generate QR codes for products, URLs, or tickets, and scan them for verification.

### Research & Analysis
Integrate OCR into data science workflows for text extraction and analysis.

## Tips & Best Practices

1. **Processing Speed**: Add delays between requests when processing many images to avoid overwhelming Umi-OCR
2. **Image Quality**: Higher quality images produce better OCR results
3. **Language Selection**: Choose the correct language model for best results
4. **Error Handling**: Always check response codes and handle failures gracefully
5. **Parallel Processing**: Use with caution (2-3 workers max) as Umi-OCR may not handle high concurrency well

## Troubleshooting

### "Cannot connect to Umi-OCR"
- Ensure Umi-OCR is running
- Check that HTTP service is enabled in Global Settings
- Verify the host and port settings match your configuration

### "No text detected" (Code 101)
- Check image quality and clarity
- Ensure the correct language model is selected
- Try adjusting OCR parameters (e.g., enable text direction correction)

### Slow processing
- Add delays between requests
- Use sequential processing instead of parallel
- Process images in smaller batches

### Connection refused errors
- Don't send too many concurrent requests
- Add delays between API calls
- Restart Umi-OCR if the issue persists

## Advanced Usage

For more advanced scenarios, refer to:
- [HTTP API Documentation](../../docs/http/README.md)
- [Command Line Documentation](../../docs/README_CLI.md)
- [Umi-OCR GitHub Repository](https://github.com/hiroi-sora/Umi-OCR)

## Contributing

Found a bug or have a suggestion? Please open an issue on the [GitHub repository](https://github.com/hiroi-sora/Umi-OCR/issues).

## License

These examples are part of the Umi-OCR project and are licensed under the same terms. See the [LICENSE](../../LICENSE) file for details.

## Acknowledgments

- **Umi-OCR**: [hiroi-sora/Umi-OCR](https://github.com/hiroi-sora/Umi-OCR)
- **PaddleOCR**: OCR engine option
- **RapidOCR**: OCR engine option
