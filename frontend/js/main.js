// API Base URL
const API_BASE_URL = 'http://localhost:8000';

// Check authentication
function checkAuth() {
    const token = localStorage.getItem('token');
    const currentPage = window.location.pathname;
    
    // Don't redirect if on home page
    if (currentPage.includes('index.html') || currentPage.endsWith('/')) {
        return true;
    }
    
    if (!token) {
        window.location.href = 'index.html';
        return false;
    }
    return true;
}

// Check admin authentication
function checkAdminAuth() {
    const token = localStorage.getItem('token');
    const role = localStorage.getItem('role');
    
    if (!token || role !== 'admin') {
        window.location.href = '../index.html';
        return false;
    }
    return true;
}

// Get auth headers
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// Student logout - Home page par jayega
function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

// Admin logout - Main home page par jayega (index.html)
function adminLogout() {
    localStorage.clear();
    window.location.href = '../index.html';  // ✅ FIXED: Back to main index.html
}

// Show notification
function showNotification(message, type = 'info') {
    // Create toast container if not exists
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
        `;
        document.body.appendChild(toastContainer);
    }
    
    // Create toast
    const toast = document.createElement('div');
    toast.style.cssText = `
        background: white;
        border-left: 4px solid ${type === 'success' ? '#10B981' : type === 'danger' ? '#EF4444' : '#F0B90B'};
        border-radius: 8px;
        padding: 16px 24px;
        margin-bottom: 10px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 300px;
        animation: slideIn 0.3s ease;
    `;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'danger' ? 'exclamation-circle' : 'info-circle';
    
    toast.innerHTML = `
        <i class="fas fa-${icon}" style="color: ${type === 'success' ? '#10B981' : type === 'danger' ? '#EF4444' : '#F0B90B'};"></i>
        <div style="flex-grow: 1;">${message}</div>
        <i class="fas fa-times" style="cursor: pointer; color: #9CA3AF;" onclick="this.parentElement.remove()"></i>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);
}

// Add keyframes (yeh ek baar add karo)
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Calculate profile completion
function calculateProfileCompletion(profile) {
    // resume_path optional hai - sirf profile data fields count honge
    const fields = ['roll_number', 'branch', 'semester', 'cgpa', 'skills'];
    let completed = 0;
    // full_name bhi count karo (users table se aata hai)
    if (profile.full_name && profile.full_name.toString().trim() !== '') completed++;
    fields.forEach(field => {
        if (profile[field] && profile[field].toString().trim() !== '') {
            completed++;
        }
    });
    return Math.round((completed / (fields.length + 1)) * 100);
}

// Load user info
async function loadUserInfo() {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        if (response.ok) {
            const user = await response.json();
            document.querySelectorAll('#userName, #userFullName').forEach(el => {
                if (el) el.textContent = user.full_name;
            });
            localStorage.setItem('userName', user.full_name);
            localStorage.setItem('userEmail', user.email);
            localStorage.setItem('userRole', user.role);
            return user;
        } else {
            // Token invalid
            localStorage.clear();
            window.location.href = 'index.html';
        }
    } catch (error) {
        console.error('Error loading user info:', error);
    }
    return null;
}

// Load admin info
async function loadAdminInfo() {
    const token = localStorage.getItem('token');
    if (!token) return null;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        if (response.ok) {
            const user = await response.json();
            document.querySelectorAll('#adminName').forEach(el => {
                if (el) el.textContent = user.full_name;
            });
            return user;
        } else {
            localStorage.clear();
            window.location.href = '../index.html';
        }
    } catch (error) {
        console.error('Error loading admin info:', error);
    }
    return null;
}

// Load notifications
async function loadNotifications() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/notifications/my-notifications?limit=5`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        if (response.ok) {
            const notifications = await response.json();
            displayNotifications(notifications);
        }
        
        const countRes = await fetch(`${API_BASE_URL}/notifications/unread-count`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
        
        if (countRes.ok) {
            const { count } = await countRes.json();
            const badge = document.getElementById('notificationBadge');
            if (badge) {
                if (count > 0) {
                    badge.style.display = 'inline';
                    badge.textContent = count;
                } else {
                    badge.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

function displayNotifications(notifications) {
    const list = document.getElementById('notificationList');
    if (!list) return;
    
    if (!notifications || notifications.length === 0) {
        list.innerHTML = '<div class="dropdown-item text-muted text-center">No notifications</div>';
        return;
    }
    
    let html = '';
    notifications.forEach(notif => {
        const bgClass = notif.is_read ? '' : 'bg-light';
        const icon = {
            'info': 'info-circle text-info',
            'success': 'check-circle text-success',
            'warning': 'exclamation-triangle text-warning',
            'danger': 'times-circle text-danger'
        }[notif.type] || 'bell text-secondary';
        
        html += `
            <div class="dropdown-item ${bgClass}" onclick="markNotificationRead(${notif.id})" style="cursor: pointer;">
                <div class="d-flex align-items-center">
                    <div class="me-2">
                        <i class="fas fa-${icon}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <strong>${notif.title}</strong>
                        <p class="mb-0 small">${notif.message}</p>
                        <small class="text-muted">${timeAgo(notif.created_at)}</small>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '<div class="dropdown-divider"></div>';
    html += '<div class="dropdown-item text-center"><a href="notifications.html" class="text-secondary">View All</a></div>';
    
    list.innerHTML = html;
}

async function markNotificationRead(id) {
    const token = localStorage.getItem('token');
    try {
        await fetch(`${API_BASE_URL}/notifications/mark-read/${id}`, {
            method: 'PUT',
            headers: {'Authorization': `Bearer ${token}`}
        });
        loadNotifications();
    } catch (error) {
        console.error('Error:', error);
    }
}

function timeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' minutes ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + ' hours ago';
    return Math.floor(seconds / 86400) + ' days ago';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const currentPage = window.location.pathname;
    
    // Set current date
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    // Load user info if logged in
    if (localStorage.getItem('token')) {
        if (currentPage.includes('admin')) {
            loadAdminInfo();
        } else {
            loadUserInfo();
        }
        
        if (document.getElementById('notificationList')) {
            loadNotifications();
            setInterval(loadNotifications, 30000);
        }
    }
});

// Add this function to check for expired drives
async function checkExpiredDrives() {
    const token = localStorage.getItem('token');
    if (!token) return;
    
    try {
        // This will trigger the auto-deactivate on backend
        await fetch(`${API_BASE_URL}/student/drives`, {
            headers: {'Authorization': `Bearer ${token}`}
        });
    } catch (error) {
        console.error('Error checking expired drives:', error);
    }
}

// Call this function periodically
setInterval(checkExpiredDrives, 60000); // Check every minute