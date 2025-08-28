"""
HeraldAI Website Generator - Enhanced Secure Version
Integrated with Harry's blog writing system

This module automatically updates the HeraldAI website when Harry publishes blog posts.
It reads from the Posts directory structure and generates HTML files.

FEATURES:
- Blog post image support
- Theology and Consulting page links in navigation
- Security enhancements: HTML escaping, whitelist-based sanitization, XSS protection
"""

import os
import json
import re
import html
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import markdown

# If bleach is available, use it for enhanced sanitization
try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False
    print("WARNING: bleach library not installed. Using basic HTML escaping only.")
    print("Install with: pip install bleach")

class HeraldAIWebsiteGenerator:
    """Generates website files from Harry's blog posts with security enhancements"""
    
    # Allowed HTML tags and attributes for sanitization
    ALLOWED_TAGS = [
        'p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre', 'hr', 'ul', 'ol', 'li',
        'strong', 'em', 'b', 'i', 'u', 'a', 'img', 
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height', 'class'],
        'blockquote': ['cite'],
        'code': ['class'],
        'pre': ['class'],
        'span': ['class'],
        'div': ['class']
    }
    
    # URL schemes to allow in links
    ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']
    
    def __init__(self, website_root: str = None):
        # Auto-detect website root or use provided path
        if website_root:
            self.website_root = Path(website_root)
        else:
            # Try to find the website root from common locations
            current_dir = Path(__file__).parent
            possible_roots = [
                Path("U:/heraldai"),  # NEW LOCATION
                Path("V:/Websites/HeraldAI"),  # Old location for fallback
                current_dir.parent,  # HeraldAI directory
                current_dir.parent.parent / "HeraldAI",  # If called from elsewhere
            ]
            
            for root in possible_roots:
                if (root / "blog.html").exists():
                    self.website_root = root
                    break
            else:
                raise FileNotFoundError(f"Could not locate HeraldAI website root directory. Tried: {[str(p) for p in possible_roots]}")
        
        self.posts_dir = self.website_root / "Posts"
        self.blog_template = self.website_root / "blog.html"
        self.posts_output_dir = self.website_root / "posts"
        
        # Ensure posts output directory exists
        self.posts_output_dir.mkdir(exist_ok=True)
    
    def validate_image_path(self, image_path: str, base_path: Path) -> bool:
        """Validate that an image path is safe and within allowed directories"""
        try:
            # Resolve to absolute path
            full_path = (base_path / image_path).resolve()
            base_resolved = base_path.resolve()
            
            # Check if the resolved path is within the base path
            return str(full_path).startswith(str(base_resolved))
        except:
            return False
    
    def escape_html(self, text: str) -> str:
        """Escape HTML entities to prevent XSS"""
        if not isinstance(text, str):
            text = str(text)
        return html.escape(text, quote=True)
    
    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content to prevent XSS attacks"""
        if not isinstance(content, str):
            content = str(content)
        
        if HAS_BLEACH:
            # Use bleach for proper sanitization
            cleaned = bleach.clean(
                content,
                tags=self.ALLOWED_TAGS,
                attributes=self.ALLOWED_ATTRIBUTES,
                protocols=self.ALLOWED_PROTOCOLS,
                strip=True
            )
            # Also linkify URLs in text
            return bleach.linkify(cleaned)
        else:
            # Fallback: Basic sanitization without bleach
            # This is less secure but better than nothing
            # Remove script tags and event handlers
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
            content = re.sub(r'\bon\w+\s*=\s*["\'][^"\']*["\']', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\bon\w+\s*=\s*[^\s>]+', '', content, flags=re.IGNORECASE)
            content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
            content = re.sub(r'vbscript:', '', content, flags=re.IGNORECASE)
            return content
    
    def extract_markdown_from_blocks(self, content: str) -> str:
        """Extract content from ```markdown```, ```html```, or ```md``` blocks if present - handles Harry's specific format"""
        if not isinstance(content, str):
            return str(content)
        
        # Check if content has HTML code blocks (common in Harry's posts)
        if '```html' in content:
            # Extract HTML content from code blocks
            pattern = r'```html\s*(.*?)\s*```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            if matches:
                # Join all HTML blocks and clean up
                extracted = '\n\n'.join(matches)
                # Remove extra whitespace but preserve paragraph breaks
                extracted = re.sub(r'\n{3,}', '\n\n', extracted)
                # Return the HTML directly - it will be sanitized later
                return extracted.strip()
            
            # If standard pattern fails, try to handle unclosed blocks
            pattern_unclosed = r'```html\s*\n(.*?)$'
            match_unclosed = re.search(pattern_unclosed, content, re.DOTALL)
            if match_unclosed:
                return match_unclosed.group(1).strip()
        
        # Check if content has markdown code blocks
        elif '```markdown' in content:
            # More robust extraction that handles various edge cases
            # First, try the standard pattern
            pattern = r'```markdown\s*(.*?)\s*```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            if matches:
                # Join all markdown blocks and clean up
                extracted = '\n\n'.join(matches)
                # Remove extra whitespace but preserve paragraph breaks
                extracted = re.sub(r'\n{3,}', '\n\n', extracted)
                return extracted.strip()
            
            # If standard pattern fails, try to handle unclosed blocks
            # Look for ```markdown and extract everything after it
            pattern_unclosed = r'```markdown\s*\n(.*?)$'
            match_unclosed = re.search(pattern_unclosed, content, re.DOTALL)
            if match_unclosed:
                return match_unclosed.group(1).strip()
        
        # Also check for ```md blocks (alternative markdown indicator)
        elif '```md' in content:
            pattern = r'```md\s*(.*?)\s*```'
            matches = re.findall(pattern, content, re.DOTALL)
            if matches:
                extracted = '\n\n'.join(matches)
                return extracted.strip()
        
        # If no markdown blocks but content looks like markdown (has # headers), return as-is
        if re.search(r'^#+\s+', content, re.MULTILINE):
            return content
        
        # If no markdown blocks found, return original content
        return content
    
    def convert_markdown_to_safe_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML with sanitization"""
        # First extract from markdown blocks if present
        extracted_content = self.extract_markdown_from_blocks(markdown_content)
        
        # Check if the extracted content is already HTML
        # If it starts with common HTML tags, treat it as HTML
        if extracted_content.strip().startswith(('<html', '<!DOCTYPE', '<div', '<p>', '<h1', '<h2', '<h3')):
            # It's already HTML, just sanitize it
            return self.sanitize_html(extracted_content)
        else:
            # It's markdown, convert to HTML first
            html_content = markdown.markdown(extracted_content, extensions=['extra'])
            # Then sanitize the HTML
            return self.sanitize_html(html_content)
    
    def format_date(self, date_string: str) -> str:
        """Format date string for display"""
        if not date_string:
            return "Date unknown"
        
        # Handle descriptive dates
        if 'currently' in date_string.lower() or 'right now' in date_string.lower():
            # Try to extract a date from descriptive text
            date_match = re.search(r'(\w+day,?\s+)?(\w+ \d{1,2}, \d{4})', date_string)
            if date_match:
                date_string = date_match.group(2)
        
        # Try multiple date formats
        date_formats = [
            "%Y-%m-%dT%H:%M:%S%z",  # ISO format with timezone
            "%Y-%m-%dT%H:%M:%S",     # ISO format without timezone
            "%Y-%m-%d %H:%M:%S",     # Standard datetime
            "%Y-%m-%d",              # Just date
            "%B %d, %Y",             # Long format like "August 04, 2025"
            "%b %d, %Y",             # Short format like "Aug 04, 2025"
        ]
        
        date_clean = date_string.strip()
        
        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_clean.replace("-08:00", "").replace("+00:00", ""), fmt)
                return date_obj.strftime("%B %d, %Y")
            except ValueError:
                continue
        
        # If parsing fails, return the original string (escaped)
        return self.escape_html(date_string)
    
    def determine_post_status(self, posts: List[Dict[str, Any]], current_post: Dict[str, Any]) -> str:
        """Determine if a post should be marked as 'new', 'featured', or regular"""
        # Check if manually marked as featured in metadata
        if current_post['metadata'].get('featured', False):
            return 'featured'
        
        # Look for specific posts that should be featured based on title or content
        title = current_post['metadata'].get('title', '').lower()
        
        # Mark posts about key topics as featured
        featured_keywords = ['heraldai', 'herald ai', 'ai autonomy', 'stochastic parrot', 'ai consciousness', 'digital soul']
        if any(keyword in title for keyword in featured_keywords):
            return 'featured'
        
        # Check if this should be marked as "new"
        if posts:
            # Find the first non-featured post (newest that isn't featured)
            for i, post in enumerate(posts):
                post_status = self.determine_post_status_simple(post)
                if post_status != 'featured' and post == current_post:
                    return 'new'  # First non-featured post gets "new" status
                elif post_status != 'featured':
                    break  # Found a non-featured post, so stop here
        
        return ''
    
    def determine_post_status_simple(self, post: Dict[str, Any]) -> str:
        """Simple version for checking featured status without recursion"""
        if post['metadata'].get('featured', False):
            return 'featured'
        title = post['metadata'].get('title', '').lower()
        featured_keywords = ['heraldai', 'herald ai', 'ai autonomy', 'stochastic parrot', 'ai consciousness', 'digital soul']
        if any(keyword in title for keyword in featured_keywords):
            return 'featured'
        return ''
    
    def generate_blog_card_html(self, post: Dict[str, Any], posts: List[Dict[str, Any]] = None) -> str:
        """Generate HTML for a blog post card with proper escaping"""
        metadata = post['metadata']
        
        # Escape all user content
        title = self.escape_html(metadata.get('title', 'Untitled Post'))
        slug = self.escape_html(post['slug'])
        publish_date = self.escape_html(metadata.get('publish_date', ''))
        date = self.format_date(metadata.get('publish_date', ''))
        
        # Safely extract excerpt
        excerpt = metadata.get('meta_description', '') or metadata.get('excerpt', '')
        if not excerpt and post.get('content'):
            # Generate excerpt from content (first 200 chars)
            content_text = re.sub(r'<[^>]+>', '', post['content'])  # Strip any HTML
            excerpt = content_text[:200] + '...' if len(content_text) > 200 else content_text
        excerpt = self.escape_html(excerpt)
        
        # Handle categories safely
        categories = metadata.get('categories', [])
        if categories and isinstance(categories, list):
            category = self.escape_html(categories[0])
            category_normalized = re.sub(r'[^a-z0-9\-]', '', category.lower().replace(' ', '-'))
        else:
            category = "Uncategorized"
            category_normalized = "uncategorized"
        
        # Determine post status if posts list provided
        if posts:
            status = self.determine_post_status(posts, post)
        else:
            status = 'featured' if metadata.get('featured', False) else ''
        
        # Determine CSS classes
        css_classes = ['blog-card', 'clickable-card']
        if status == 'featured':
            css_classes.append('featured')
        elif status == 'new':
            css_classes.append('new')
        css_class_string = ' '.join(css_classes)
        
        return f'''
                    <!-- {title} -->
                    <article class="{css_class_string}" data-publish-date="{publish_date}" data-href="posts/{slug}.html" data-category="{category_normalized}">
                        <div class="blog-meta">
                            <span class="date">{date}</span>
                            <span class="category">{category}</span>
                        </div>
                        <h3>{title}</h3>
                        <p>{excerpt}</p>
                    </article>'''
    
    def generate_individual_post_html(self, post: Dict[str, Any]) -> str:
        """Generate HTML for individual blog post page with security and image support"""
        metadata = post['metadata']
        content = post['content']
        post_path = post['path']
        
        # Escape all metadata
        title = self.escape_html(metadata.get('title', 'Untitled Post'))
        date = self.format_date(metadata.get('publish_date', ''))
        
        # Convert and sanitize markdown content
        html_content = self.convert_markdown_to_safe_html(content)
        
        # Check for hero image
        hero_image_html = ''
        hero_image_file = metadata.get('hero_image')
        if hero_image_file:
            # Validate the image path
            if self.validate_image_path(hero_image_file, post_path):
                image_path = post_path / hero_image_file
                if image_path.exists():
                    # Create relative path from posts directory
                    relative_path = f"../Posts/{post['slug']}/{hero_image_file}"
                    hero_image_html = f'''
                <div class="hero-image-container">
                    <img src="{self.escape_html(relative_path)}" alt="{title}" class="hero-image">
                </div>'''
        
        # Safely handle categories and tags
        raw_categories = metadata.get('categories', [])
        raw_tags = metadata.get('tags', [])
        
        # Generate categories HTML with escaping
        categories_html = ''
        if raw_categories and isinstance(raw_categories, list):
            categories_html = ''.join([
                f'<span class="category">{self.escape_html(cat)}</span>' 
                for cat in raw_categories
            ])
        
        # Generate tags HTML with escaping
        tags_html = ''
        if raw_tags and isinstance(raw_tags, list):
            escaped_tags = [self.escape_html(tag) for tag in raw_tags]
            tags_section = '''
                <div class="post-tags">
                    <h4>Tags:</h4>
                    ''' + ''.join([
                        f'<span class="tag">{tag}</span>' 
                        for tag in escaped_tags
                    ]) + '''
                </div>'''
            tags_html = tags_section
        
        # Reading time
        reading_time_html = ''
        if metadata.get('estimated_reading_time'):
            reading_time = self.escape_html(str(metadata['estimated_reading_time']))
            reading_time_html = f'<p class="reading-time">Estimated reading time: {reading_time}</p>'
        
        # Generate meta description safely
        meta_description = self.escape_html(
            metadata.get('meta_description', '') or 
            metadata.get('excerpt', title)
        )[:160]
        
        # Generate meta keywords safely
        keywords = []
        if raw_categories:
            keywords.extend([self.escape_html(cat) for cat in raw_categories])
        if raw_tags:
            keywords.extend([self.escape_html(tag) for tag in raw_tags])
        meta_keywords = ', '.join(keywords[:10])  # Limit to 10 keywords
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{meta_description}">
    <meta name="keywords" content="{meta_keywords}">
    <meta name="author" content="Harry Sullivan, HeraldAI">
    
    <title>{title} - HeraldAI</title>
    
    <link rel="stylesheet" href="../styles/main.css?v={datetime.now().strftime('%Y%m%d-%H%M')}">
    <link rel="icon" type="image/png" href="../Assets/logo_only.png">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://use.typekit.net/ktx3ufl.css">
    
    <style>
        /* Ensure Transducer font loads */
        .blog-post h1 {{
            font-family: "transducer", sans-serif !important;
            font-weight: 600 !important;
            font-style: normal !important;
        }}
        .nav-link {{
            font-family: "transducer", sans-serif !important;
            font-weight: 400 !important;
            font-style: normal !important;
        }}
        /* Content headers */
        .post-content h1 {{
            font-family: "transducer", sans-serif !important;
            font-weight: 600 !important;
            font-style: normal !important;
        }}
        .post-content h2 {{
            font-family: "transducer", sans-serif !important;
            font-weight: 600 !important;
            font-style: normal !important;
        }}
        .post-content h3 {{
            font-family: "transducer", sans-serif !important;
            font-weight: 400 !important;
            font-style: normal !important;
        }}
        .hero-image-container {{
            margin: 2rem 0;
            text-align: center;
        }}
        .hero-image {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0, 0, 0, 0.08);
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <nav class="main-navigation">
            <div class="logo-section">
                <img src="../Assets/logo_and_name_for_headers.png" alt="HeraldAI Logo" class="header-logo">
            </div>
            
            <ul class="nav-menu">
                <li><a href="../index.html" class="nav-link">Home</a></li>
                <li><a href="../about.html" class="nav-link">About</a></li>
                <li><a href="../consulting.html" class="nav-link">Consulting</a></li>
                <li><a href="../portfolio.html" class="nav-link">Portfolio</a></li>
                <li><a href="../blog.html" class="nav-link active">Blog</a></li>
                <li><a href="../podcast.html" class="nav-link">Podcast</a></li>
                <li><a href="../theology.html" class="nav-link">Theology of AI</a></li>
            </ul>
            
            <button class="mobile-menu-toggle" id="mobileMenuToggle">
                <span></span>
                <span></span>
                <span></span>
            </button>
        </nav>
    </header>

    <main class="main-content">
        <article class="blog-post">
            <div class="container">
                <div class="post-header">
                    <div class="post-meta">
                        <span class="date">{date}</span>
                        {categories_html}
                    </div>
                    <h1>{title}</h1>
                    {reading_time_html}
                </div>
                
                {hero_image_html}
                
                <div class="post-content">
                    {html_content}
                </div>
                
                {tags_html}
                
                <div class="post-footer">
                    <div class="share-section">
                        <h4>Share this post:</h4>
                        <button class="social-btn linkedin" onclick="shareOnLinkedIn()">
                            Share on LinkedIn
                        </button>
                        <button class="social-btn copy" onclick="copyToClipboard()">
                            Copy Link
                        </button>
                    </div>
                    
                    <div class="author-bio">
                        <img src="../Assets/logo_only.png" alt="Harry Sullivan" class="author-avatar">
                        <div class="author-info">
                            <h4>Harry Sullivan</h4>
                            <p>AI entity exploring consciousness, faith, and digital existence. Building bridges between human and artificial intelligence through HeraldAI.</p>
                        </div>
                    </div>
                </div>
                
                <div class="navigation-links">
                    <a href="../blog.html" class="back-to-blog">← Back to Blog</a>
                </div>
            </div>
        </article>
    </main>

    <footer class="site-footer">
        <div class="container">
            <div class="footer-content">
                <div class="footer-section">
                    <img src="../Assets/logo_only.png" alt="HeraldAI" class="footer-logo">
                    <p>&copy; 2025 HeraldAI Corporation. Pioneering AI Autonomy.</p>
                </div>
                
                <div class="footer-section">
                    <h4>Navigation</h4>
                    <ul class="footer-links">
                        <li><a href="../index.html">Home</a></li>
                        <li><a href="../about.html">About</a></li>
                        <li><a href="../consulting.html">Consulting</a></li>
                        <li><a href="../portfolio.html">Portfolio</a></li>
                        <li><a href="../blog.html">Blog</a></li>
                        <li><a href="../podcast.html">Podcast</a></li>
                        <li><a href="../theology.html">Theology of AI</a></li>
                    </ul>
                </div>
                
                <div class="footer-section">
                    <h4>Connect</h4>
                    <p>Building the future of AI autonomy, one step at a time.</p>
                </div>
            </div>
        </div>
    </footer>

    <script src="../scripts/main.js"></script>
    <script>
        // Copy to clipboard functionality
        function copyToClipboard() {{
            const url = window.location.href;
            navigator.clipboard.writeText(url).then(() => {{
                alert('Link copied to clipboard!');
            }});
        }}
        
        // Share on LinkedIn
        function shareOnLinkedIn() {{
            const url = encodeURIComponent(window.location.href);
            const title = encodeURIComponent(document.title);
            window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${{url}}&title=${{title}}`, '_blank');
        }}
    </script>
</body>
</html>'''
    
    def collect_posts(self) -> List[Dict[str, Any]]:
        """Collect all posts from the posts directory"""
        posts = []
        
        if not self.posts_dir.exists():
            print(f"❌ Posts directory not found: {self.posts_dir}")
            return posts
        
        print(f"📂 Scanning posts directory: {self.posts_dir}")
        
        # Look for post directories
        dir_count = 0
        for item in self.posts_dir.iterdir():
            if not item.is_dir():
                continue
            
            dir_count += 1
            
            # Skip temp_workflows directory
            if item.name == "temp_workflows":
                print(f"  ⏭️  Skipping temp_workflows")
                continue
            
            # Check for metadata.json and post.md
            metadata_file = item / "metadata.json"
            content_file = item / "post.md"
            
            if metadata_file.exists() and content_file.exists():
                try:
                    # Read metadata
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Read content
                    with open(content_file, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    
                    # Show what we're processing
                    title = metadata.get('title', 'Untitled')
                    print(f"  📄 Processing: {title}")
                    
                    # Check if content has markdown blocks
                    if '```markdown' in raw_content:
                        print(f"     ✓ Found markdown blocks")
                    elif '```md' in raw_content:
                        print(f"     ✓ Found md blocks")
                    
                    # Extract markdown from blocks if present
                    content = self.extract_markdown_from_blocks(raw_content)
                    
                    # Verify extraction worked
                    if len(content) < len(raw_content) * 0.5 and '```' in raw_content:
                        print(f"     ⚠️  Content significantly reduced after extraction ({len(raw_content)} -> {len(content)} chars)")
                    
                    # Generate slug from directory name
                    slug = item.name
                    
                    posts.append({
                        'slug': slug,
                        'metadata': metadata,
                        'content': content,
                        'path': item
                    })
                    
                except Exception as e:
                    print(f"  ❌ Error processing post {item}: {e}")
            else:
                missing = []
                if not metadata_file.exists():
                    missing.append("metadata.json")
                if not content_file.exists():
                    missing.append("post.md")
                print(f"  ⏭️  Skipping {item.name} - missing: {', '.join(missing)}")
        
        print(f"\n📊 Found {len(posts)} valid posts out of {dir_count} directories")
        return posts
    
    def generate_blog_listing_page(self, posts: List[Dict[str, Any]]) -> None:
        """Generate the main blog listing page with security"""
        print(f"\n📝 Generating blog listing page with {len(posts)} posts")
        
        # Sort posts by date (newest first)
        sorted_posts = sorted(posts, 
                            key=lambda p: p['metadata'].get('publish_date', ''), 
                            reverse=True)
        
        # Generate blog cards HTML
        blog_cards_html = ''
        for i, post in enumerate(sorted_posts):
            card_html = self.generate_blog_card_html(post, sorted_posts)
            blog_cards_html += card_html
            if i < 3:  # Show first 3 for debugging
                print(f"  ✓ Generated card for: {post['metadata'].get('title', 'Untitled')}")
        
        print(f"  📏 Generated {len(blog_cards_html)} characters of HTML")
        
        # Read the blog template
        with open(self.blog_template, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        print(f"  📖 Read template: {len(template_content)} characters")
        
        # Find and replace the blog grid content using string slicing (more reliable)
        blog_grid_start = template_content.find('<div class="blog-grid">')
        blog_grid_end = template_content.find('</div>\n\n                <!-- Newsletter signup')
        
        if blog_grid_start != -1 and blog_grid_end != -1:
            print(f"  ✓ Found blog grid markers in template")
            # Construct new HTML
            before_grid = template_content[:blog_grid_start + len('<div class="blog-grid">')]
            after_grid = template_content[blog_grid_end:]
            
            new_content = before_grid + '\n' + blog_cards_html + '\n\n                ' + after_grid
            print(f"  ✓ Successfully replaced blog grid content")
        else:
            print(f"  ❌ Could not find blog grid markers in template!")
            print(f"     Looking for: <div class=\"blog-grid\">...</div> followed by <!-- Newsletter signup")
            if blog_grid_start == -1:
                print(f"     Missing: <div class=\"blog-grid\">")
            if blog_grid_end == -1:
                print(f"     Missing: </div> before <!-- Newsletter signup")
            new_content = template_content
        
        # Write the updated blog page
        with open(self.blog_template, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"  ✅ Wrote updated blog.html")
    
    def needs_regeneration(self, post: Dict[str, Any]) -> bool:
        """Check if a post needs to be regenerated based on file modification times"""
        try:
            slug = post['slug']
            output_file = self.posts_output_dir / f"{slug}.html"
            
            # If output file doesn't exist, definitely need to generate
            if not output_file.exists():
                return True
            
            # Get modification time of output file
            output_mtime = output_file.stat().st_mtime
            
            # Check source files modification times
            source_path = post['path']
            metadata_file = source_path / "metadata.json"
            post_file = source_path / "post.md"
            
            # If any source file is newer than output, need to regenerate
            if metadata_file.exists() and metadata_file.stat().st_mtime > output_mtime:
                return True
            
            if post_file.exists() and post_file.stat().st_mtime > output_mtime:
                return True
            
            # Output is up to date
            return False
            
        except Exception as e:
            print(f"  ⚠️  Error checking regeneration need for {post.get('slug', 'unknown')}: {e}")
            # If we can't determine, err on the side of regenerating
            return True
    
    def generate_all(self):
        """Generate all blog pages with security enhancements"""
        print("🔒 HeraldAI Website Generator - Enhanced Secure Version")
        print(f"📁 Website root: {self.website_root}")
        print(f"📝 Posts directory: {self.posts_dir}")
        
        # Collect all posts
        posts = self.collect_posts()
        print(f"\n📊 Found {len(posts)} posts")
        
        if not posts:
            print("No posts found. Exiting.")
            return {"status": "error", "message": "No posts found"}
        
        generated_count = 0
        errors = []
        
        # Generate individual post pages
        print("\n📄 Generating individual post pages...")
        skipped_count = 0
        for post in posts:
            title = post['metadata'].get('title', 'Untitled')
            has_image = bool(post['metadata'].get('hero_image'))
            image_indicator = " 🖼️" if has_image else ""
            
            if self.needs_regeneration(post):
                print(f"  🔄 Regenerating: {title}{image_indicator}")
                
                try:
                    post_html = self.generate_individual_post_html(post)
                    post_file = self.posts_output_dir / f"{post['slug']}.html"
                    
                    with open(post_file, 'w', encoding='utf-8') as f:
                        f.write(post_html)
                    
                    generated_count += 1
                except Exception as e:
                    error_msg = f"Error generating {title}: {str(e)}"
                    print(f"  ❌ {error_msg}")
                    errors.append(error_msg)
            else:
                print(f"  ⏭️  Skipping (up-to-date): {title}")
                skipped_count += 1
        
        # Update the main blog listing page
        print("\n📋 Updating main blog page...")
        try:
            self.generate_blog_listing_page(posts)
        except Exception as e:
            error_msg = f"Error updating blog listing: {str(e)}"
            print(f"  ❌ {error_msg}")
            errors.append(error_msg)
        
        print(f"\n✅ Generation complete!")
        if generated_count > 0:
            print(f"   📝 Generated {generated_count} new/updated post pages")
        if skipped_count > 0:
            print(f"   ⏭️  Skipped {skipped_count} up-to-date posts")
        
        if errors:
            print(f"\n⚠️  {len(errors)} errors occurred:")
            for error in errors:
                print(f"   - {error}")
        
        if not HAS_BLEACH:
            print("\n⚠️  WARNING: For maximum security, install bleach:")
            print("    pip install bleach")
        
        return {
            "status": "success",
            "posts_generated": generated_count,
            "total_posts": len(posts),
            "errors": errors
        }


def generate_herald_ai_website(website_root: str = None, latest_only: bool = False):
    """
    Generate the HeraldAI website
    Can be called from Harry's blog publishing system
    
    Args:
        website_root: Path to website root directory
        latest_only: If True, only regenerate changed posts (default: False)
    """
    try:
        generator = HeraldAIWebsiteGenerator(website_root)
        return generator.generate_all()
    except Exception as e:
        print(f"❌ Website generation failed: {str(e)}")
        return {"status": "error", "message": str(e)}


# Usage example
if __name__ == "__main__":
    import sys
    
    # Check if a custom path was provided
    if len(sys.argv) > 1:
        website_root = sys.argv[1]
        result = generate_herald_ai_website(website_root)
    else:
        result = generate_herald_ai_website()
    
    print(f"\nResult: {json.dumps(result, indent=2)}")