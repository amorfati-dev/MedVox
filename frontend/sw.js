/**
 * MedVox Service Worker
 * Provides offline functionality and fast loading
 */

const CACHE_NAME = 'medvox-v1.0.0';
const API_CACHE_NAME = 'medvox-api-v1.0.0';

// Files to cache for offline use
const STATIC_CACHE_FILES = [
    '/',
    '/index.html',
    '/styles.css',
    '/app.js',
    '/manifest.json'
];

// API endpoints to cache
const API_CACHE_URLS = [
    '/health',
    '/api/v1/documentation/supported-formats'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker');
    
    event.waitUntil(
        Promise.all([
            // Cache static files
            caches.open(CACHE_NAME).then((cache) => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_CACHE_FILES);
            }),
            
            // Skip waiting to activate immediately
            self.skipWaiting()
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then((cacheNames) => {
                return Promise.all(
                    cacheNames.map((cacheName) => {
                        if (cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME) {
                            console.log('[SW] Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            
            // Take control of all clients
            self.clients.claim()
        ])
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle different types of requests
    if (request.method !== 'GET') {
        // Don't cache non-GET requests (like POST for audio uploads)
        return fetch(request);
    }
    
    // Handle API requests
    if (url.pathname.startsWith('/api/') || url.pathname === '/health') {
        event.respondWith(handleAPIRequest(request));
        return;
    }
    
    // Handle static files
    event.respondWith(handleStaticRequest(request));
});

/**
 * Handle API requests with network-first strategy
 */
async function handleAPIRequest(request) {
    const url = new URL(request.url);
    
    // For audio upload endpoints, always go to network
    if (url.pathname.includes('/process-audio')) {
        try {
            return await fetch(request);
        } catch (error) {
            // Show offline message for critical endpoints
            return new Response(
                JSON.stringify({
                    success: false,
                    error_message: 'Keine Internetverbindung. Bitte später versuchen.',
                    offline: true
                }),
                {
                    status: 503,
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }
    }
    
    // For other API endpoints, try network first, then cache
    try {
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(API_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Try to serve from cache
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response
        return new Response(
            JSON.stringify({
                success: false,
                error_message: 'Offline - Cached data not available',
                offline: true
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }
}

/**
 * Handle static file requests with cache-first strategy
 */
async function handleStaticRequest(request) {
    // Try cache first
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }
    
    // Try network if not in cache
    try {
        const networkResponse = await fetch(request);
        
        // Cache the response for next time
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        // Return offline page for navigation requests
        if (request.mode === 'navigate') {
            const offlineResponse = await caches.match('/index.html');
            return offlineResponse || new Response('Offline', { status: 503 });
        }
        
        throw error;
    }
}

// Background sync for saving documentation when back online
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);
    
    if (event.tag === 'save-documentation') {
        event.waitUntil(syncDocumentation());
    }
});

/**
 * Sync saved documentation when back online
 */
async function syncDocumentation() {
    try {
        // Get saved documentations from IndexedDB or localStorage
        const savedDocs = await getSavedDocumentations();
        
        for (const doc of savedDocs) {
            if (!doc.synced) {
                try {
                    await uploadDocumentation(doc);
                    doc.synced = true;
                    await updateDocumentation(doc);
                } catch (error) {
                    console.error('[SW] Failed to sync documentation:', error);
                }
            }
        }
    } catch (error) {
        console.error('[SW] Background sync failed:', error);
    }
}

/**
 * Get saved documentations (placeholder - implement with IndexedDB)
 */
async function getSavedDocumentations() {
    // This would typically use IndexedDB
    // For now, return empty array
    return [];
}

/**
 * Upload documentation to server
 */
async function uploadDocumentation(doc) {
    const response = await fetch('/api/v1/documentation/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(doc)
    });
    
    if (!response.ok) {
        throw new Error('Failed to upload documentation');
    }
    
    return response.json();
}

/**
 * Update documentation status
 */
async function updateDocumentation(doc) {
    // Update in IndexedDB or localStorage
    console.log('[SW] Documentation synced:', doc.id);
}

// Handle push notifications (future feature)
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    if (event.data) {
        const data = event.data.json();
        
        event.waitUntil(
            self.registration.showNotification(data.title, {
                body: data.body,
                icon: '/icon-192.png',
                badge: '/icon-192.png',
                tag: 'medvox-notification',
                data: data.data
            })
        );
    }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked');
    
    event.notification.close();
    
    event.waitUntil(
        clients.openWindow('/')
    );
});

// Handle messages from the main app
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
}); 