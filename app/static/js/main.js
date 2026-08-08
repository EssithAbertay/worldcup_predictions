async function updateNotificationButton() {
    const button = document.getElementById('enable-notifications');

    if (!button) return;

    if (!('Notification' in window)) {
        button.textContent = 'Notifications unavailable';
        button.disabled = true;
        return;
    }

    if (Notification.permission === 'denied') {
        button.textContent = '🔕 Notifications blocked';
        button.disabled = true;
        return;
    }

    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();

    if (subscription) {
        button.textContent = '✓ Notifications enabled';
        button.classList.remove('btn-outline-primary');
        button.classList.add('btn-success');
    } else {
        button.textContent = '🔔 Enable notifications';
    }
}

updateNotificationButton();


if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then(registration => {
                console.log('Service worker registered:', registration);
            })
            .catch(error => {
                console.error('Service worker registration failed:', error);
            });
    });
}

function hexToUint8Array(hexString) {
    const bytes = new Uint8Array(hexString.length / 2);

    for (let i = 0; i < hexString.length; i += 2) {
        bytes[i / 2] = parseInt(hexString.substring(i, i + 2), 16);
    }

    return bytes;
}

const notificationButton = document.getElementById('enable-notifications');

if (notificationButton) {
    notificationButton.addEventListener('click', async () => {
        try {
            const permission = await Notification.requestPermission();

            if (permission !== 'granted') {
                console.log('Notification permission not granted');
                return;
            }

            const vapidResponse = await fetch('/vapid-public-key');

            if (!vapidResponse.ok) {
                throw new Error('Could not retrieve VAPID public key');
            }

            const vapidPublicKey = await vapidResponse.text();

            const registration = await navigator.serviceWorker.ready;

            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: hexToUint8Array(vapidPublicKey)
            });

            console.log('Push subscription:', subscription);

            const saveResponse = await fetch('/save-push-subscription', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(subscription.toJSON())
            });

            if (!saveResponse.ok) {
                throw new Error('Could not save push subscription');
            }

            const result = await saveResponse.json();

            if (result.success) {
                console.log('Push subscription saved!');
            } else {
                console.error('Failed to save push subscription');
            }

        } catch (error) {
            console.error('Push subscription failed:', error);
        }
    });
}