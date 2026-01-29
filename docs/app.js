/**
 * AI News Aggregator - Frontend Application
 */

// State
let articles = [];
let filteredArticles = [];
let allTags = [];
let currentFilters = {
    source: 'all',
    date: 'all',
    search: '',
    tags: [],
    sort: 'interest_score'
};

// DOM Elements
const articlesContainer = document.getElementById('articles-container');
const searchInput = document.getElementById('search-input');
const tagsContainer = document.getElementById('tags-container');
const articleCount = document.getElementById('article-count');
const lastUpdated = document.getElementById('last-updated');
const sortSelect = document.getElementById('sort-select');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadArticles();
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
            lastUpdated.textContent = `最終更新: ${formatDate(date)}`;
        }

        // Extract all unique tags
        allTags = [...new Set(articles.flatMap(a => a.tags || []))].sort();
        renderTags();

        // Apply filters and render
        applyFilters();
    } catch (error) {
        console.error('Error loading articles:', error);
        articlesContainer.innerHTML = '<div class="no-results">記事の読み込みに失敗しました</div>';
    }
}

// Setup event listeners
function setupEventListeners() {
    // Search
    searchInput.addEventListener('input', debounce((e) => {
        currentFilters.search = e.target.value.toLowerCase();
        applyFilters();
    }, 300));

    // Source filter
    document.querySelectorAll('[data-source]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-source]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilters.source = btn.dataset.source;
            applyFilters();
        });
    });

    // Date filter
    document.querySelectorAll('[data-date]').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('[data-date]').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilters.date = btn.dataset.date;
            applyFilters();
        });
    });

    // Sort
    sortSelect.addEventListener('change', (e) => {
        currentFilters.sort = e.target.value;
        applyFilters();
    });
}

// Render tags
function renderTags() {
    tagsContainer.innerHTML = allTags.map(tag =>
        `<button class="tag-btn" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`
    ).join('');

    // Add tag click listeners
    tagsContainer.querySelectorAll('.tag-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tag = btn.dataset.tag;
            if (currentFilters.tags.includes(tag)) {
                currentFilters.tags = currentFilters.tags.filter(t => t !== tag);
                btn.classList.remove('active');
            } else {
                currentFilters.tags.push(tag);
                btn.classList.add('active');
            }
            applyFilters();
        });
    });
}

// Apply filters
function applyFilters() {
    filteredArticles = articles.filter(article => {
        // Source filter
        if (currentFilters.source !== 'all') {
            if (!article.source.includes(currentFilters.source)) return false;
        }

        // Date filter
        if (currentFilters.date !== 'all') {
            const articleDate = new Date(article.created_at || article.fetched_at);
            const now = new Date();

            if (currentFilters.date === 'today') {
                const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                if (articleDate < todayStart) return false;
            } else if (currentFilters.date === 'week') {
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                if (articleDate < weekAgo) return false;
            }
        }

        // Search filter
        if (currentFilters.search) {
            const searchText = [
                article.title,
                article.summary,
                ...(article.tags || [])
            ].join(' ').toLowerCase();

            if (!searchText.includes(currentFilters.search)) return false;
        }

        // Tags filter
        if (currentFilters.tags.length > 0) {
            const articleTags = article.tags || [];
            if (!currentFilters.tags.some(tag => articleTags.includes(tag))) return false;
        }

        return true;
    });

    // Sort
    sortArticles();

    // Update count
    articleCount.textContent = `${filteredArticles.length}件の記事`;

    // Render
    renderArticles();
}

// Sort articles
function sortArticles() {
    filteredArticles.sort((a, b) => {
        switch (currentFilters.sort) {
            case 'interest_score':
                return (b.interest_score || 0) - (a.interest_score || 0);
            case 'created_at':
                return new Date(b.created_at || b.fetched_at) - new Date(a.created_at || a.fetched_at);
            case 'comments_count':
                return (b.comments_count || 0) - (a.comments_count || 0);
            case 'source_score':
                return (b.source_score || 0) - (a.source_score || 0);
            default:
                return 0;
        }
    });
}

// Render articles
function renderArticles() {
    if (filteredArticles.length === 0) {
        articlesContainer.innerHTML = '<div class="no-results">該当する記事がありません</div>';
        return;
    }

    articlesContainer.innerHTML = filteredArticles.map(article => {
        const score = article.interest_score || 0;
        const scoreClass = score >= 15 ? '' : score >= 5 ? 'medium' : 'low';
        const sourceClass = getSourceClass(article.source);
        const timeAgo = getTimeAgo(article.created_at || article.fetched_at);

        return `
            <div class="article-card">
                <div class="article-header">
                    <a href="${escapeHtml(article.url)}" target="_blank" rel="noopener noreferrer" class="article-title">
                        ${escapeHtml(article.title)}
                    </a>
                    <span class="article-score ${scoreClass}">Score: ${score}</span>
                </div>
                ${article.summary ? `<p class="article-summary">${escapeHtml(article.summary)}</p>` : ''}
                <div class="article-meta">
                    <div class="article-tags">
                        ${(article.tags || []).map(tag =>
                            `<span class="article-tag">${escapeHtml(tag)}</span>`
                        ).join('')}
                    </div>
                    <span class="article-source ${sourceClass}">${escapeHtml(article.source)}</span>
                    <span class="article-time">${timeAgo}</span>
                    ${article.comments_url ? `
                        <span class="article-comments">
                            <a href="${escapeHtml(article.comments_url)}" target="_blank" rel="noopener noreferrer">
                                ${article.comments_count || 0} comments
                            </a>
                        </span>
                    ` : ''}
                </div>
                ${(article.matched_keywords || []).length > 0 ? `
                    <div class="matched-keywords">
                        Matched: ${article.matched_keywords.join(', ')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

// Utility functions
function getSourceClass(source) {
    if (source.includes('Hacker News')) return 'hn';
    if (source.includes('Reddit')) return 'reddit';
    if (source.includes('GitHub')) return 'github';
    return '';
}

function getTimeAgo(dateString) {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 60) return `${diffMins}分前`;
    if (diffHours < 24) return `${diffHours}時間前`;
    if (diffDays < 7) return `${diffDays}日前`;
    return formatDate(date);
}

function formatDate(date) {
    return date.toLocaleDateString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
