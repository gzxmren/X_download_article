import os
import pytest
from unittest.mock import MagicMock
from src.exporter import Exporter

def test_to_pdf_calls_playwright(tmp_path):
    """Test that to_pdf navigates to the file and calls page.pdf."""
    # 1. Setup
    mock_page = MagicMock()
    html_path = tmp_path / "test.html"
    html_path.write_text("<h1>Test</h1>", encoding="utf-8")
    pdf_path = tmp_path / "test.pdf"
    
    # 2. Execute
    success = Exporter.to_pdf(mock_page, str(html_path), str(pdf_path))
    
    # 3. Verify
    assert success is True
    # Verify navigation happened (file protocol)
    mock_page.goto.assert_called_once()
    args, _ = mock_page.goto.call_args
    assert args[0].startswith("file://")
    assert args[0].endswith("test.html")
    
    # Verify PDF generation was triggered
    mock_page.pdf.assert_called_once_with(
        path=str(pdf_path),
        format="A4",
        margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
        print_background=True
    )

def test_to_epub_structure(tmp_path, mocker):
    """Test that to_epub assembles the book and writes it."""
    # 1. Mock the external library (ebooklib.write_epub) to avoid actual complex file writing
    #    We just want to know if our logic constructs the book correctly.
    mock_write = mocker.patch("ebooklib.epub.write_epub")
    
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    # Create a dummy image
    (assets_dir / "test.jpg").write_bytes(b"fake_image_data")
    
    html_content = """
    <html>
        <body>
            <h1>Title</h1>
            <p>Text</p>
            <img src="assets/test.jpg" />
        </body>
    </html>
    """
    
    output_path = str(tmp_path / "output.epub")
    
    # 2. Execute
    success = Exporter.to_epub(
        title="Test Book",
        author="Tester",
        html_content=html_content,
        assets_dir=str(assets_dir),
        output_epub_path=output_path
    )
    
    # 3. Verify
    assert success is True
    mock_write.assert_called_once()
    
    # Inspect arguments passed to write_epub
    # args[0] is path, args[1] is the book object
    call_args = mock_write.call_args
    assert call_args[0][0] == output_path
    
    book = call_args[0][1]
    assert book.title == "Test Book"
    # Check if image was added
    # This is deep inspection, but ensures our image processing logic works
    image_items = [item for item in book.items if item.media_type == 'image/jpeg']
    assert len(image_items) == 1
    assert image_items[0].uid == "test.jpg"
