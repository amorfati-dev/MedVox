// MedVox Service Worker - Minimal Implementation
// Prevents 404 errors for sw.js requests

const CACHE_NAME = 'medvox-v1';

// Install event
self.addEventListener('install', (event) => {
  console.log('MedVox Service Worker installed');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('MedVox Service Worker activated');
  event.waitUntil(self.clients.claim());
});

// Fetch event (minimal - just let requests pass through)
self.addEventListener('fetch', (event) => {
  // For now, just let all requests go to the network
  // Future: Add offline caching for audio files, etc.
}); 