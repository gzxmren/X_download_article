import os
import uuid
from bs4 import BeautifulSoup
from playwright.sync_api import Page
from ebooklib import epub
from .logger import logger

class Exporter:
    @staticmethod
    def to_pdf(page: Page, local_html_path: str, output_pdf_path: str):
        """
        Renders the local HTML file in Playwright and prints it to PDF.
        """
        try:
            # Convert to absolute file URI
            abs_path = os.path.abspath(local_html_path)
            file_uri = f"file://{abs_path}"
            
            logger.info(f"Generating PDF: {output_pdf_path}")
            
            # Navigate to local file
            # waitUntil networkidle ensures images are loaded
            page.goto(file_uri, wait_until="networkidle")
            
            # Print PDF
            page.pdf(
                path=output_pdf_path,
                format="A4",
                margin={"top": "20px", "bottom": "20px", "left": "20px", "right": "20px"},
                print_background=True
            )
            return True
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return False

    @staticmethod
    def to_epub(title: str, author: str, html_content: str, assets_dir: str, output_epub_path: str):
        """
        Packages the HTML content and local images into an EPUB file.
        """
        try:
            logger.info(f"Generating EPUB: {output_epub_path}")
            
            book = epub.EpubBook()
            
            # Metadata
            book.set_identifier(str(uuid.uuid4()))
            book.set_title(title)
            book.set_language('en')
            book.add_author(author)
            
            # Parse HTML to process images
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Process Images
            epub_images = []
            for img in soup.find_all('img'):
                src = img.get('src')
                # src is like "assets/hash.jpg" or relative path
                if not src:
                    continue
                    
                # Calculate absolute local path
                # assets_dir is the full path to assets folder
                # img src is relative to article.html, e.g. "assets/abc.jpg"
                filename = os.path.basename(src)
                local_img_path = os.path.join(assets_dir, filename)
                
                if os.path.exists(local_img_path):
                    # Create EpubImage item
                    # Internal path in EPUB: static/filename
                    epub_img_path = f"static/{filename}"
                    
                    with open(local_img_path, 'rb') as f:
                        img_content = f.read()
                        
                    epub_img = epub.EpubImage()
                    epub_img.uid = filename
                    epub_img.file_name = epub_img_path
                    epub_img.media_type = 'image/jpeg' # Assuming JPG for now based on downloader
                    epub_img.content = img_content
                    
                    book.add_item(epub_img)
                    epub_images.append(epub_img)
                    
                    # Update HTML src to point to internal EPUB path
                    img['src'] = epub_img_path
                else:
                    logger.warning(f"EPUB: Image not found at {local_img_path}")

            # Create Main Chapter
            c1 = epub.EpubHtml(title='Article', file_name='article.xhtml', lang='en')
            c1.content = str(soup)
            book.add_item(c1)
            
            # Structure
            book.toc = (c1, )
            book.spine = ['nav', c1]
            book.add_item(epub.EpubNcx())
            book.add_item(epub.EpubNav())
            
            # Write
            epub.write_epub(output_epub_path, book, {})
            return True
            
        except Exception as e:
            logger.error(f"EPUB generation failed: {e}")
            return False
