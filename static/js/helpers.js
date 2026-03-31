/**
 * Rapid Cash - Premium Dark FinTech Dashboard
 * JavaScript Helpers
 * 
 * Contains: Modal management, Toast notifications, Fee calculator,
 * HTMX utilities, and UI helpers
 */

// ============================================
// Toast Notifications
// ============================================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    const icons = {
        success: '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
        error: '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>',
        warning: '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>',
        info: '<svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
    };

    toast.className = `toast toast-${type} animate-slide-in mb-3`;
    toast.innerHTML = `
        <div class="flex items-center gap-3">
            ${icons[type] || icons.info}
            <span>${message}</span>
        </div>
    `;

    container.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

function clearToasts() {
    const container = document.getElementById('toast-container');
    if (container) {
        container.innerHTML = '';
    }
}

// ============================================
// Modal Management
// ============================================

function openModal(title, content, actions = '') {
    const container = document.getElementById('modal-container');
    if (!container) return;

    container.innerHTML = `
        <div class="modal-overlay fixed inset-0 z-50 flex items-center justify-center p-4" onclick="if(event.target === this) closeModal()">
            <div class="modal-content w-full max-w-lg animate-fade-in">
                <div class="flex items-center justify-between p-5 border-b border-border">
                    <h3 class="text-lg font-bold text-fg font-display tracking-tight">${title}</h3>
                    <button onclick="closeModal()" class="p-1.5 hover:bg-muted transition-colors text-muted-fg hover:text-fg">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                <div class="p-5">${content}</div>
                ${actions ? `<div class="flex justify-end gap-3 p-5 pt-0">${actions}</div>` : ''}
            </div>
        </div>
    `;
    document.body.style.overflow = 'hidden';

    // Add escape key listener
    document.addEventListener('keydown', handleEscapeKey);
}

function closeModal() {
    const container = document.getElementById('modal-container');
    if (container) {
        container.innerHTML = '';
    }
    document.body.style.overflow = '';
    document.removeEventListener('keydown', handleEscapeKey);
}

function handleEscapeKey(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
}

// HTMX modal loader
function loadModalContent(url, title) {
    fetch(url)
        .then(response => response.text())
        .then(html => openModal(title, html))
        .catch(err => showToast('Erreur lors du chargement', 'error'));
}

// ============================================
// Fee Calculator
// ============================================

// Fee grid configuration
let feeGrid = typeof window.SERVER_FEE_GRID !== 'undefined' && window.SERVER_FEE_GRID.length > 0
    ? window.SERVER_FEE_GRID
    : [
        { min: 0.10, max: 40, fee: 5 },
        { min: 40.01, max: 100, fee: 8 },
        { min: 100.01, max: 200, fee: 15 },
        { min: 200.01, max: 300, fee: 20 },
        { min: 300.01, max: 400, fee: 26 },
        { min: 400.01, max: 600, fee: 30 },
        { min: 600.01, max: 800, fee: 35 },
        { min: 800.01, max: 1000, fee: 40 },
        { min: 1000.01, max: 1500, fee: 45 },
        { min: 1500.01, max: 1800, fee: 64 },
        { min: 1800.01, max: 2000, fee: 80 }
    ];

function calculateFee(amount) {
    if (!amount || amount < 0.10 || feeGrid.length === 0) return 0;

    for (const tier of feeGrid) {
        if (amount >= tier.min && amount <= tier.max) {
            return tier.fee;
        }
    }
    // For amounts above max tier, calculate proportionally
    const lastTier = feeGrid[feeGrid.length - 1];
    if (amount > lastTier.max) {
        const excess = amount - lastTier.max;
        return lastTier.fee + Math.ceil(excess / 100) * 5;
    }
    return 0;
}

function updateFeePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (input && preview) {
        const amount = parseFloat(input.value) || 0;
        const fee = calculateFee(amount);
        const total = amount + fee;

        preview.innerHTML = `
            <div class="space-y-2 text-sm">
                <div class="flex justify-between">
                    <span class="text-muted-fg">Montant:</span>
                    <span class="font-mono text-fg">$${amount.toFixed(2)}</span>
                </div>
                <div class="flex justify-between text-status-success">
                    <span>Frais:</span>
                    <span class="font-mono">+$${fee.toFixed(2)}</span>
                </div>
                <div class="flex justify-between font-bold text-lg pt-2 border-t border-border">
                    <span>Total:</span>
                    <span class="font-mono text-accent">$${total.toFixed(2)}</span>
                </div>
            </div>
        `;
    }
}

// ============================================
// HTMX Utilities
// ============================================

// Refresh KPIs (called after operations)
function htmxRefreshKPIs() {
    const kpiGrid = document.getElementById('kpi-grid');
    if (kpiGrid && typeof htmx !== 'undefined') {
        htmx.ajax('GET', window.location.pathname + '?hx=kpi', {
            target: '#kpi-grid',
            swap: 'innerHTML'
        }).then(() => {
            showToast('Données mises à jour', 'success');
        });
    }
}

// Show loading indicator
function showIndicator(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.add('htmx-indicator');
    }
}

function hideIndicator(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.remove('htmx-indicator');
    }
}

// HTMX event handlers
document.addEventListener('htmx:beforeSwap', function (event) {
    // Handle errors
    if (event.detail.xhr.status >= 400) {
        showToast('Une erreur est survenue', 'error');
    }
});

document.addEventListener('htmx:afterSwap', function (event) {
    // Reinitialize components after HTMX swap
    initTooltips();
});

document.addEventListener('htmx:responseError', function (event) {
    showToast('Erreur de connexion', 'error');
});

// ============================================
// Currency Formatting
// ============================================

function formatCurrency(amount, currency = 'USD', locale = 'fr-FR') {
    return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

function formatNumber(number, decimals = 2) {
    return number.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ============================================
// Date/Time Utilities
// ============================================

function formatDate(date, format = 'short') {
    const d = new Date(date);

    if (format === 'short') {
        return d.toLocaleDateString('fr-FR');
    } else if (format === 'long') {
        return d.toLocaleDateString('fr-FR', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } else if (format === 'time') {
        return d.toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    return d.toLocaleDateString('fr-FR');
}

// Update clock in header
function updateClock() {
    const dateEl = document.getElementById('current-date');
    const timeEl = document.getElementById('current-time');

    if (dateEl && timeEl) {
        const now = new Date();
        dateEl.textContent = now.toLocaleDateString('fr-FR', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        timeEl.textContent = now.toLocaleTimeString('fr-FR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', function () {
    // Initialize clock
    updateClock();
    setInterval(updateClock, 1000);

    // Initialize tooltips
    initTooltips();

    // Show Django messages as toasts from data attribute
    const messagesContainer = document.getElementById('django-messages');
    if (messagesContainer) {
        const messages = JSON.parse(messagesContainer.dataset.messages || '[]');
        messages.forEach(msg => {
            showToast(msg.text, msg.level === 'error' ? 'error' : 'success');
        });
    }
});

// Simple tooltip initialization
function initTooltips() {
    // Tooltip logic can be added here
    // For now, using title attributes is sufficient
}

// ============================================
// Export for global use
// ============================================

window.RapidCash = {
    showToast,
    clearToasts,
    openModal,
    closeModal,
    loadModalContent,
    calculateFee,
    updateFeePreview,
    htmxRefreshKPIs,
    formatCurrency,
    formatNumber,
    formatDate,
    updateClock
};
