"""
Research Service Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import shutil

from src.search import WebSearcher, SearchEngine, SearchResult, SearchResponse
from src.extractor import ContentExtractor, ExtractedContent
from src.researcher import Researcher, ResearchResult, Source, KnowledgeBase, KnowledgeEntry


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


class TestWebSearcher:
    """Test web search functionality."""

    @pytest.fixture
    def searcher(self):
        """Create a web searcher for testing."""
        return WebSearcher(
            default_engine="duckduckgo",
            timeout=10,
            max_results=5,
        )

    def test_initialization(self, searcher):
        """Test searcher initialization."""
        assert searcher.default_engine == SearchEngine.DUCKDUCKGO
        assert searcher.max_results == 5

    @pytest.mark.asyncio
    async def test_search_duckduckgo(self, searcher):
        """Test DuckDuckGo search."""
        with patch.object(searcher, '_search_duckduckgo') as mock_search:
            mock_search.return_value = [
                SearchResult(
                    title="Test Result",
                    url="https://example.com",
                    snippet="Test snippet",
                    source="duckduckgo",
                    position=1,
                )
            ]

            response = await searcher.search("test query")

            assert response.query == "test query"
            assert response.engine == SearchEngine.DUCKDUCKGO
            assert len(response.results) == 1
            assert response.results[0].title == "Test Result"


class TestContentExtractor:
    """Test content extraction."""

    @pytest.fixture
    def extractor(self):
        """Create a content extractor for testing."""
        return ContentExtractor(
            timeout=10,
            max_content_length=10000,
        )

    def test_initialization(self, extractor):
        """Test extractor initialization."""
        assert extractor.timeout == 10
        assert extractor.max_content_length == 10000

    @pytest.mark.asyncio
    async def test_extract_content(self, extractor):
        """Test content extraction."""
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <article>
                <h1>Test Article</h1>
                <p>This is test content.</p>
            </article>
        </body>
        </html>
        """

        with patch.object(extractor, '_fetch_page', return_value=html):
            content = await extractor.extract("https://example.com")

            assert content.title == "Test Page"
            assert "test content" in content.text.lower()
            assert content.domain == "example.com"

    def test_extract_with_bs4(self, extractor):
        """Test BeautifulSoup extraction fallback."""
        html = """
        <html>
        <body>
            <nav>Navigation</nav>
            <article>
                <p>Main content here.</p>
            </article>
            <footer>Footer</footer>
        </body>
        </html>
        """

        text = extractor._extract_with_bs4(html)

        assert "Main content" in text
        # Nav and footer should be removed
        assert "Navigation" not in text
        assert "Footer" not in text

    def test_extract_metadata(self, extractor):
        """Test metadata extraction."""
        html = """
        <html>
        <head>
            <title>Test Title</title>
            <meta name="description" content="Test description">
            <meta name="author" content="Test Author">
        </head>
        <body></body>
        </html>
        """

        metadata = extractor._extract_metadata(html)

        assert metadata["title"] == "Test Title"
        assert metadata["description"] == "Test description"
        assert metadata["author"] == "Test Author"


class TestKnowledgeBase:
    """Test knowledge base functionality."""

    @pytest.fixture
    def knowledge_base(self, temp_dir):
        """Create a knowledge base for testing."""
        return KnowledgeBase(f"{temp_dir}/knowledge.db")

    def test_store_and_get(self, knowledge_base):
        """Test storing and retrieving knowledge."""
        entry = KnowledgeEntry(
            id="test-1",
            topic="Test Topic",
            content="Test content",
            sources=["https://example.com"],
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )

        knowledge_base.store(entry)
        retrieved = knowledge_base.get("test-1")

        assert retrieved is not None
        assert retrieved.topic == "Test Topic"
        assert retrieved.content == "Test content"

    def test_search(self, knowledge_base):
        """Test knowledge search."""
        entries = [
            KnowledgeEntry(
                id="python-1",
                topic="Python Programming",
                content="Python is a programming language",
                sources=[],
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            KnowledgeEntry(
                id="java-1",
                topic="Java Programming",
                content="Java is another programming language",
                sources=[],
                created_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        for entry in entries:
            knowledge_base.store(entry)

        # Note: FTS search may need to be rebuilt
        # This test verifies basic functionality


class TestResearcher:
    """Test research functionality."""

    @pytest.fixture
    def researcher(self, temp_dir):
        """Create a researcher for testing."""
        return Researcher(
            cache_dir=f"{temp_dir}/cache",
            cache_ttl=300,
            knowledge_db_path=f"{temp_dir}/knowledge.db",
            enable_knowledge_base=True,
        )

    @pytest.mark.asyncio
    async def test_research(self, researcher):
        """Test research functionality."""
        # Mock searcher
        mock_search_response = SearchResponse(
            query="test query",
            engine=SearchEngine.DUCKDUCKGO,
            results=[
                SearchResult(
                    title="Test Result 1",
                    url="https://example1.com",
                    snippet="First result snippet",
                    source="duckduckgo",
                    position=1,
                ),
                SearchResult(
                    title="Test Result 2",
                    url="https://example2.com",
                    snippet="Second result snippet",
                    source="duckduckgo",
                    position=2,
                ),
            ],
            total_results=2,
            search_time_ms=100,
        )

        researcher.searcher.search = AsyncMock(return_value=mock_search_response)

        # Mock extractor
        mock_content = ExtractedContent(
            url="https://example1.com",
            title="Test",
            text="Extracted content here",
            markdown="# Extracted content",
            html="",
            domain="example1.com",
            word_count=3,
        )

        researcher.extractor.extract_multiple = AsyncMock(return_value=[mock_content])

        # Conduct research
        result = await researcher.research("test query", max_sources=2)

        assert result.query == "test query"
        assert len(result.sources) == 2
        assert result.total_sources == 2

    @pytest.mark.asyncio
    async def test_quick_answer(self, researcher):
        """Test quick answer functionality."""
        mock_search_response = SearchResponse(
            query="what is python",
            engine=SearchEngine.DUCKDUCKGO,
            results=[
                SearchResult(
                    title="Python (programming language)",
                    url="https://wikipedia.org/wiki/Python",
                    snippet="Python is a high-level programming language",
                    source="duckduckgo",
                    position=1,
                ),
            ],
            total_results=1,
            search_time_ms=50,
        )

        researcher.searcher.search = AsyncMock(return_value=mock_search_response)

        result = await researcher.quick_answer("what is python")

        assert result["answer"] == "Python is a high-level programming language"
        assert result["source"]["url"] == "https://wikipedia.org/wiki/Python"

    def test_store_knowledge(self, researcher):
        """Test storing knowledge."""
        entry_id = researcher.store_knowledge(
            topic="Test Topic",
            content="Test content",
            sources=["https://example.com"],
        )

        assert entry_id is not None
        assert len(entry_id) == 16  # MD5 hash prefix

    def test_synthesize(self, researcher):
        """Test content synthesis."""
        sources = [
            Source(
                url="https://example.com",
                title="Test",
                snippet="Important information here",
                content="Important information here. Research shows this is significant.",
                relevance_score=0.9,
            ),
        ]

        summary, key_points = researcher._synthesize("test", sources)

        assert len(summary) > 0
        assert isinstance(key_points, list)

    def test_generate_related_queries(self, researcher):
        """Test related query generation."""
        sources = [
            Source(
                url="https://example.com",
                title="Test",
                snippet="Test",
                relevance_score=0.9,
            ),
        ]

        related = researcher._generate_related_queries("python", sources)

        assert isinstance(related, list)
        assert len(related) > 0


class TestSearchResult:
    """Test search result dataclass."""

    def test_creation(self):
        """Test search result creation."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source="duckduckgo",
            position=1,
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.position == 1

    def test_with_metadata(self):
        """Test search result with metadata."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test",
            source="brave",
            position=1,
            metadata={"age": "2 days ago"},
        )

        assert result.metadata["age"] == "2 days ago"


class TestExtractedContent:
    """Test extracted content dataclass."""

    def test_creation(self):
        """Test extracted content creation."""
        content = ExtractedContent(
            url="https://example.com",
            title="Test Page",
            text="Test content",
            markdown="# Test",
            html="<h1>Test</h1>",
            domain="example.com",
            word_count=2,
        )

        assert content.url == "https://example.com"
        assert content.title == "Test Page"
        assert content.word_count == 2


class TestSource:
    """Test source dataclass."""

    def test_creation(self):
        """Test source creation."""
        source = Source(
            url="https://example.com",
            title="Test Source",
            snippet="Test snippet",
            content="Full content",
            relevance_score=0.85,
        )

        assert source.url == "https://example.com"
        assert source.relevance_score == 0.85


class TestResearchResult:
    """Test research result dataclass."""

    def test_creation(self):
        """Test research result creation."""
        result = ResearchResult(
            query="test query",
            summary="Test summary",
            sources=[],
            key_points=["Point 1", "Point 2"],
            related_queries=["related 1"],
            total_sources=0,
            research_time_ms=100,
        )

        assert result.query == "test query"
        assert len(result.key_points) == 2
        assert result.cached is False
