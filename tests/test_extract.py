from src.extract.structured import extract_structured_data, find_social_links
from src.extract.text import extract_main_text


def test_extract_structured_data():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Test Org"
        }
        </script>
      </head>
      <body></body>
    </html>
    """
    data = extract_structured_data(html, "https://example.com")
    assert "json-ld" in data
    assert len(data["json-ld"]) == 1
    assert data["json-ld"][0]["name"] == "Test Org"


def test_find_social_links():
    html = '<html><body><a href="https://linkedin.com/company/test">LinkedIn</a></body></html>'
    links = find_social_links(html)
    assert "https://linkedin.com/company/test" in links


def test_extract_main_text():
    html = "<html><body><h1>Title</h1><p>Main content paragraph here.</p></body></html>"
    text = extract_main_text(html)
    assert "Main content paragraph here." in text
    assert "Title" in text
