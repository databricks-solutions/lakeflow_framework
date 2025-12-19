from sphinx_markdown_builder.translator import MarkdownTranslator
from sphinx_markdown_builder.builder import MarkdownBuilder
from sphinx_markdown_builder.writer import MarkdownWriter

from docutils import nodes

class CustomMarkdownTranslator(MarkdownTranslator):
    """Custom Markdown Translator for Sphinx. Extends the default Markdown translator, only overriding specific directives."""

    def __init__(self, document, builder):
        super().__init__(document, builder)
        self.has_raw_html = False
        self.css_link_added = False
        # Check if document contains any raw HTML nodes
        for child in document.traverse(nodes.raw):
            if 'html' in child.get('format', ''):
                self.has_raw_html = True
                break
    
    def visit_raw(self, node):
        """Handle raw nodes, including CSS references"""
        if 'html' in node.get('format', ''):
            # Add CSS link before the first raw HTML content if not already added
            if self.has_raw_html and not self.css_link_added:
                self.add('<link rel="stylesheet" type="text/css" href="_static/custom.css">\n\n')
                self.css_link_added = True
            text = node.astext()
            self.add(text + '\n')
        raise nodes.SkipNode

    def visit_admonition(self, node):
        # Check if it's a 'note' block
        classes = node.get("classes", [])
        if "note" in classes:
            self.add("\n> [!NOTE]\n")  # Markdown blockquote with bold title
            self.add("> " + "\n> ".join(line.strip() for line in node.astext().split("\n")))
            self.add("\n\n")
        elif "important" in classes:
            self.add("\n> [!IMPORTANT]\n")  # Markdown blockquote with bold title
            self.add("> " + "\n> ".join(line.strip() for line in node.astext().split("\n")))
            self.add("\n\n")
        raise nodes.SkipNode
    
    def visit_warning(self, node):
        """Convert .. warning:: directive to Markdown blockquote format"""
        self.add("\n> [!WARNING]\n")  # Markdown blockquote with bold title
        self.add("> " + "\n> ".join(line.strip() for line in node.astext().split("\n")))
        self.add("\n\n")
        raise nodes.SkipNode

    def visit_note(self, node):
        """Convert .. note:: directive to Markdown blockquote format"""
        self.add("\n> [!NOTE]\n")  # Markdown blockquote with bold title
        self.add("> " + "\n> ".join(line.strip() for line in node.astext().split("\n")))
        self.add("\n\n")
        raise nodes.SkipNode
    
    # def visit_enumerated_list(self, node):
    #     """Handle enumerated lists (numbered or lettered)"""
    #     enumtype = node.get('enumtype', 'arabic')
    #     start = node.get('start', 1)
        
    #     if enumtype == 'arabic':
    #         self.enumerated_list_style.append(('1', start))
    #     elif enumtype == 'loweralpha':
    #         self.enumerated_list_style.append(('a', string.ascii_lowercase.index(str(start)) if str(start).isalpha() else 0))
    #     elif enumtype == 'upperalpha':
    #         self.enumerated_list_style.append(('A', string.ascii_uppercase.index(str(start)) if str(start).isalpha() else 0))
    #     else:
    #         self.enumerated_list_style.append(('1', start))  # Default to numbers
            
    #     self.list_depth += 1

    # def depart_enumerated_list(self, node):
    #     """Handle end of enumerated lists"""
    #     self.list_depth -= 1
    #     if self.enumerated_list_style:
    #         self.enumerated_list_style.pop()

    # def visit_list_item(self, node):
    #     """Handle list items with proper formatting"""
    #     self._start_list_item(node)

    # def depart_list_item(self, node):
    #     self.add("\n")

    # def visit_block_quote(self, node):
    #     self.add(">"+" " * self.indent_level)
    
    # def visit_topic(self, node):
    #     self.add(" " * self.indent_level)
    #     self.add("\n".join(line.strip() for line in node.astext().split("\n")))

    def visit_important(self, node):
        """Convert .. important:: directive to Markdown blockquote format"""
        self.add("\n> [!IMPORTANT]\n")  # Markdown blockquote with bold title
        self.add("> " + "\n> ".join(line.strip() for line in node.astext().split("\n")))
        self.add("\n\n")
        raise nodes.SkipNode

    def visit_RawHtmlNode(self, node):
        self.add("\n" + node.astext() + "\n")  # Insert raw HTML directly
        raise nodes.SkipNode  # Skip further processing

class CustomMarkdownWriter(MarkdownWriter):
    translator_class = CustomMarkdownTranslator

class CustomMarkdownBuilder(MarkdownBuilder):
    name = 'markdown'  # Override the default markdown builder
    writer_class = CustomMarkdownWriter

def setup(app):
    """Register the custom markdown builder with Sphinx."""
    # Register all required config values
    app.add_config_value('markdown_http_base', '', 'env')
    app.add_config_value('markdown_uri_doc_suffix', '.md', 'env')
    app.add_config_value('markdown_anchor_sections', True, 'env')
    app.add_config_value('markdown_docinfo', False, 'env')
    app.add_config_value('markdown_bullet', '*', 'env')
    app.add_builder(CustomMarkdownBuilder)
    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }