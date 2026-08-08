self.addEventListener('install', event => {
    console.log('Service worker installing');
});

self.addEventListener('activate', event => {
    console.log('Service worker activated');
});

self.addEventListener('push', event => {
    const data = event.data.json();

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body
        })
    );
});