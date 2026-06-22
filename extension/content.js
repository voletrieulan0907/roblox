// Content script - runs on Roblox.com page
// Extracts user info from meta tags and communicates with background script

console.log('🔗 [CONTENT SCRIPT] Loaded on Roblox.com');

// Extract user info from meta tags
function extractUserInfo() {
    try {
        const userDataMeta = document.querySelector('meta[name="user-data"]');
        if (!userDataMeta) {
            console.log('[CONTENT] No user-data meta tag found');
            return null;
        }

        const userId = userDataMeta.getAttribute('data-userid');
        const username = userDataMeta.getAttribute('data-name');

        if (userId && username) {
            console.log(`[CONTENT] Extracted user: ${username} (${userId})`);
            return {
                id: parseInt(userId),
                name: username
            };
        }
    } catch (error) {
        console.error('[CONTENT] Error extracting user info:', error);
    }
    return null;
}

// Send message to background script
function sendToBackground(userInfo) {
    if (!userInfo) {
        console.log('[CONTENT] No user info to send');
        return;
    }

    chrome.runtime.sendMessage({
        type: 'USER_INFO_EXTRACTED',
        payload: userInfo
    }, (response) => {
        if (chrome.runtime.lastError) {
            console.error('[CONTENT] Message error:', chrome.runtime.lastError);
            return;
        }
        console.log('[CONTENT] Message sent to background:', response);
    });
}

// Extract and send immediately
const userInfo = extractUserInfo();
sendToBackground(userInfo);

// Also listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === 'GET_USER_INFO') {
        sendResponse({ userInfo: extractUserInfo() });
    }
});

console.log('✨ [CONTENT SCRIPT] Ready');
