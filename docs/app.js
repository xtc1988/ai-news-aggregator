/**
 * AI新聞 - フロントエンドアプリケーション
 * 新聞スタイル ニュースアグリゲーター
 */

// State
let articles = [];
let filteredArticles = [];
let currentSource = 'all';
let currentSort = 'score';
let searchQuery = '';

// DOM Elements
const featuredContainer = document.getElementById('featuredArticle');
const grid = document.getElementById('articlesGrid');
const emptyState = document.getElementById('emptyState');
const searchInput = document.getElementById('searchInput');
const sortSelect = document.getElementById('sortSelect');
const articleCountEl = document.getElementById('articleCount');
const lastUpdatedEl = document.getElementById('lastUpdated');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadArticles();
    setupEventListeners();
});

// Load articles from JSON
async function loadArticles() {
    try {
        const response = await fetch('data/articles.json');
        if (!response.ok) throw new Error('Failed to fetch articles');

        const data = await response.json();
        articles = data.articles || [];

        // Update last updated
        if (data.last_updated) {
            const date = new Date(data.last_updated);
            lastUpdatedEl.textContent = formatNewspaperDate(date);
        }

        filterAndRender();
    } catch (error) {
        console.error('Error loading articles:', error);
        featuredContainer.innerHTML = '<p class="text-center text-gray-500 py-8">記事の読み込みに失敗しました</p>';
    }
}

// Setup event listeners
function setupEventListeners() {
    // Search
    searchInput.addEventListener('input', debounce((e) => {
        searchQuery = e.target.value.toLowerCase();
        filterAndRender();
    }, 300));

    // Sort
    sortSelect.addEventListener('change', (e) => {
        currentSort = e.target.value;
        filterAndRender();
    });

    // Source filters
    document.querySelectorAll('.source-filter').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.source-filter').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSource = btn.dataset.source;
            filterAndRender();
        });
    });
}

// Filter and render
function filterAndRender() {
    filteredArticles = articles.filter(article => {
        // Source filter
        if (currentSource !== 'all') {
            if (currentSource === 'Reddit') {
                if (!article.source.includes('Reddit')) return false;
            } else if (!article.source.includes(currentSource)) {
                return false;
            }
        }

        // Search filter
        if (searchQuery) {
            const titleMatch = article.title.toLowerCase().includes(searchQuery);
            const summaryMatch = article.summary && article.summary.toLowerCase().includes(searchQuery);
            const keywordMatch = (article.matched_keywords || []).some(k => k.toLowerCase().includes(searchQuery));
            const tagMatch = (article.tags || []).some(t => t.toLowerCase().includes(searchQuery));
            if (!titleMatch && !summaryMatch && !keywordMatch && !tagMatch) return false;
        }

        return true;
    });

    // Sort
    filteredArticles.sort((a, b) => {
        switch (currentSort) {
            case 'score':
                return (b.interest_score || 0) - (a.interest_score || 0);
            case 'date':
                return new Date(b.created_at || b.fetched_at) - new Date(a.created_at || a.fetched_at);
            case 'comments':
                return (b.comments_count || 0) - (a.comments_count || 0);
            default:
                return 0;
        }
    });

    renderArticles();
}

// Render articles
function renderArticles() {
    articleCountEl.textContent = `${filteredArticles.length} 件の記事`;

    if (filteredArticles.length === 0) {
        featuredContainer.classList.add('hidden');
        grid.classList.add('hidden');
        emptyState.classList.remove('hidden');
        return;
    }

    featuredContainer.classList.remove('hidden');
    grid.classList.remove('hidden');
    emptyState.classList.add('hidden');

    // Featured article (first one with highest score)
    const featured = filteredArticles[0];
    featuredContainer.innerHTML = `
        <article>
            <div class="flex items-center gap-4 mb-4 text-sm flex-wrap">
                <span class="uppercase tracking-wider font-semibold">${escapeHtml(featured.source)}</span>
                <span class="text-gray-500">|</span>
                <span class="dateline">${formatArticleDate(featured.created_at)}</span>
                <span class="text-gray-500">|</span>
                <span class="font-semibold">スコア: ${featured.interest_score || 0}</span>
            </div>

            <h2 class="text-3xl md:text-4xl lg:text-5xl font-black leading-tight mb-6">
                <a href="${escapeHtml(featured.url)}" target="_blank" rel="noopener noreferrer" class="hover:underline decoration-2">
                    ${escapeHtml(featured.title)}
                </a>
            </h2>

            ${featured.summary ? `
                <div class="multi-column">
                    <p class="drop-cap text-lg leading-relaxed">${escapeHtml(featured.summary)}</p>
                </div>
            ` : ''}

            ${(featured.matched_keywords || []).length > 0 ? `
                <div class="flex flex-wrap gap-4 mt-6 text-sm">
                    ${featured.matched_keywords.map(keyword => `
                        <span class="uppercase tracking-wider text-gray-600">${escapeHtml(keyword)}</span>
                    `).join('<span class="text-gray-400">|</span>')}
                </div>
            ` : ''}

            <div class="mt-4">
                <a href="${escapeHtml(featured.comments_url)}" target="_blank" rel="noopener noreferrer" class="text-sm italic hover:underline">
                    ディスカッションに参加 (${featured.comments_count || 0} コメント) &rarr;
                </a>
            </div>
        </article>
    `;

    // Remaining articles (up to 15)
    const remaining = filteredArticles.slice(1, 16);
    grid.innerHTML = remaining.map((article, index) => `
        <article class="${index < 2 ? 'md:col-span-1' : ''} pb-6 mb-6 border-b border-gray-300">
            <div class="text-xs uppercase tracking-wider text-gray-600 mb-2">
                ${escapeHtml(article.source)}
            </div>

            <h3 class="text-xl font-bold leading-snug mb-3">
                <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="hover:underline">
                    ${escapeHtml(article.title)}
                </a>
            </h3>

            ${article.summary ? `
                <p class="text-sm text-gray-700 leading-relaxed mb-3 line-clamp-3">${escapeHtml(article.summary)}</p>
            ` : ''}

            <div class="flex items-center justify-between text-xs text-gray-500 flex-wrap gap-2">
                <span class="dateline">${formatArticleDate(article.created_at)}</span>
                <div class="flex items-center gap-3">
                    <span class="font-semibold">スコア: ${article.interest_score || 0}</span>
                    <a href="${escapeHtml(article.comments_url)}" target="_blank" class="hover:underline">${article.comments_count || 0} コメント</a>
                </div>
            </div>

            ${(article.matched_keywords || []).length > 0 ? `
                <div class="mt-3 text-xs text-gray-600">
                    ${article.matched_keywords.slice(0, 3).map(k => `<span class="italic">${escapeHtml(k)}</span>`).join(', ')}
                </div>
            ` : ''}
        </article>
    `).join('');
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNewspaperDate(date) {
    const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    return date.toLocaleDateString('ja-JP', options);
}

function formatArticleDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('ja-JP', options);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
