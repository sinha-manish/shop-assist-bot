// Shop Assist Smart Apparel Assistant - Frontend JavaScript
class ChatApp {
    constructor() {
        // Configure socket.io with increased timeout and better reconnection settings
        this.socket = io({
            timeout: 60000, // Increase timeout to 60 seconds (default is 20s)
            reconnection: true,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            reconnectionAttempts: Infinity,
            transports: ['websocket', 'polling'], // Try websocket first, fallback to polling
            upgrade: true,
            rememberUpgrade: true
        });
        this.chatMessages = document.getElementById('chatMessages');
        this.chatWindow = document.getElementById('chatWindow'); // Scrollable container
        this.messageInput = document.getElementById('messageInput');
        this.sendButton = document.getElementById('sendButton');
        this.clearButton = document.getElementById('clearButton');
        this.voiceButton = document.getElementById('voiceButton');
        this.voiceStatus = document.getElementById('voiceStatus');
        this.voiceStatusText = document.getElementById('voiceStatusText');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        
        // Voice assistance
        this.recognition = null;
        this.isListening = false;
        this.synthesis = window.speechSynthesis;
        this.isSpeaking = false;
        this.lastInputWasVoice = false; // Track if last input was from voice
        this.initVoiceRecognition();
        
        this.chatHistory = [];
        this.isLoading = false;
        this.skeletonMessage = null; // Track skeleton loader
        this.cart = JSON.parse(sessionStorage.getItem('cart') || '[]'); // Session cart
        this.cartButton = document.getElementById('cartButton');
        this.cartBadge = document.getElementById('cartBadge');
        this.userButton = document.getElementById('userButton');
        this.userStatus = document.getElementById('userStatus');
        this.verifiedEmail = sessionStorage.getItem('verifiedEmail') || null;
        this.verificationTimestamp = sessionStorage.getItem('verificationTimestamp') || null;
        this.userName = sessionStorage.getItem('userName') || null;
        this.userPhone = sessionStorage.getItem('userPhone') || null;
        this.userGender = sessionStorage.getItem('userGender') || null;
        
        // Check if session is still valid (24 hours)
        this.checkSessionValidity();
        
        // Initialize cart display
        this.updateCartDisplay();
        
        // Initialize user button display
        this.updateUserButtonDisplay();
        
        // Debug: Check socket connection
        this.socket.on('connect', () => {
            console.log('✅ Socket connected:', this.socket.id);
            console.log('✅ Socket connected status:', this.socket.connected);
            console.log('✅ Transport:', this.socket.io.engine.transport.name);
        });
        this.socket.on('disconnect', (reason) => {
            console.log('❌ Socket disconnected:', reason);
            if (reason === 'io server disconnect') {
                // Server disconnected the socket, reconnect manually
                this.socket.connect();
            }
        });
        this.socket.on('connect_error', (error) => {
            console.error('❌ Socket connection error:', error);
            // Don't show timeout errors as critical if connection eventually succeeds
            if (error.message && error.message.includes('timeout')) {
                console.warn('⚠️ Connection timeout - will retry automatically');
            }
        });
        this.socket.on('reconnect', (attemptNumber) => {
            console.log('✅ Socket reconnected after', attemptNumber, 'attempts');
        });
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            console.log('🔄 Reconnection attempt', attemptNumber);
        });
        this.socket.on('reconnect_error', (error) => {
            console.error('❌ Reconnection error:', error);
        });
        this.socket.on('reconnect_failed', () => {
            console.error('❌ Reconnection failed - please refresh the page');
        });
        
        // Test socket event reception (if onAny is available)
        if (typeof this.socket.onAny === 'function') {
            this.socket.onAny((event, ...args) => {
                console.log('📡 Socket event received:', event, args);
            });
        }
        
        this.initializeEventListeners();
        this.initializeSocketListeners();
        this.initializeAutoScroll();
        this.initializeCartButton();
        this.initializeUserButton();
        this.initializeQuestionSuggestions();
    }
    
    initializeUserButton() {
        if (this.userButton) {
            this.userButton.addEventListener('click', () => {
                if (this.isVerified()) {
                    this.showAccountModal();
                } else {
                    this.showLoginModal();
                }
            });
        }
    }
    
    updateUserButtonDisplay() {
        if (!this.userButton || !this.userStatus) return;
        
        if (this.isVerified()) {
            // Show user as logged in
            const displayName = this.userName || this.verifiedEmail.split('@')[0];
            this.userStatus.textContent = displayName.substring(0, 10) + (displayName.length > 10 ? '...' : '');
            this.userButton.classList.add('verified');
            this.userButton.title = `Logged in as ${this.verifiedEmail}`;
        } else {
            // Show login prompt
            this.userStatus.textContent = 'Login';
            this.userButton.classList.remove('verified');
            this.userButton.title = 'Click to login';
        }
    }
    
    showLoginModal() {
        const modal = document.createElement('div');
        modal.id = 'loginModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10001';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '32px';
        modalContent.style.maxWidth = '450px';
        modalContent.style.width = '90%';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                <h2 style="margin: 0; color: #1a1a1a; font-size: 1.5rem;">
                    <i class="fas fa-user-circle" style="color: #667eea; margin-right: 10px;"></i>
                    Login / Sign Up
                </h2>
                <button id="closeLoginModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <p style="color: #666; margin-bottom: 24px; font-size: 0.9rem;">
                Login to access your purchase history, saved items, and personalized recommendations.
            </p>
            <form id="loginForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Full Name *</label>
                    <input type="text" id="loginName" required placeholder="Enter your name" 
                        style="width: 100%; padding: 12px 16px; border: 2px solid #e5e5e5; border-radius: 10px; font-size: 14px; box-sizing: border-box; transition: border-color 0.2s;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Email Address *</label>
                    <input type="email" id="loginEmail" required placeholder="example@email.com"
                        style="width: 100%; padding: 12px 16px; border: 2px solid #e5e5e5; border-radius: 10px; font-size: 14px; box-sizing: border-box; transition: border-color 0.2s;">
                    <p id="emailError" style="margin-top: 4px; font-size: 0.75rem; color: #ef4444; display: none;">
                        Please enter a valid email address
                    </p>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Phone Number * <span style="font-weight: 400; color: #888;">(10 digits)</span></label>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="padding: 12px; background: #f3f4f6; border-radius: 10px; color: #666; font-weight: 600;">+91</span>
                        <input type="tel" id="loginPhone" required placeholder="9876543210" maxlength="10"
                            style="flex: 1; padding: 12px 16px; border: 2px solid #e5e5e5; border-radius: 10px; font-size: 14px; box-sizing: border-box; transition: border-color 0.2s;">
                    </div>
                    <p id="phoneError" style="margin-top: 4px; font-size: 0.75rem; color: #ef4444; display: none;">
                        Please enter a valid 10-digit phone number
                    </p>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">I'm shopping for *</label>
                    <div style="display: flex; gap: 10px;">
                        <label style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 12px; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; transition: all 0.2s;" id="genderMaleLabel">
                            <input type="radio" name="loginGender" value="male" id="genderMale" style="display: none;">
                            <span style="font-size: 20px; margin-right: 8px;">👨</span>
                            <span style="font-weight: 600;">Men</span>
                        </label>
                        <label style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 12px; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; transition: all 0.2s;" id="genderFemaleLabel">
                            <input type="radio" name="loginGender" value="female" id="genderFemale" style="display: none;">
                            <span style="font-size: 20px; margin-right: 8px;">👩</span>
                            <span style="font-weight: 600;">Women</span>
                        </label>
                        <label style="flex: 1; display: flex; align-items: center; justify-content: center; padding: 12px; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; transition: all 0.2s;" id="genderKidLabel">
                            <input type="radio" name="loginGender" value="kid" id="genderKid" style="display: none;">
                            <span style="font-size: 20px; margin-right: 8px;">👶</span>
                            <span style="font-weight: 600;">Kids</span>
                        </label>
                    </div>
                    <p id="genderError" style="margin-top: 4px; font-size: 0.75rem; color: #ef4444; display: none;">
                        Please select who you're shopping for
                    </p>
                </div>
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Verification Code *</label>
                    <div style="display: flex; gap: 10px;">
                        <input type="text" id="loginCode" required placeholder="6-digit code" maxlength="6"
                            style="flex: 1; padding: 12px 16px; border: 2px solid #e5e5e5; border-radius: 10px; font-size: 14px; box-sizing: border-box; letter-spacing: 3px; text-align: center;">
                        <button type="button" id="sendLoginCode" 
                            style="padding: 12px 16px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 13px; white-space: nowrap;">
                            Send Code
                        </button>
                    </div>
                    <p style="margin-top: 8px; font-size: 0.75rem; color: #888;">
                        <i class="fas fa-info-circle"></i> Demo: Any 6-digit code works
                    </p>
                </div>
                <button type="submit" 
                    style="width: 100%; padding: 14px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 16px; transition: transform 0.2s, box-shadow 0.2s;">
                    <i class="fas fa-sign-in-alt" style="margin-right: 8px;"></i>
                    Login
                </button>
            </form>
            <p style="margin-top: 16px; font-size: 0.8rem; color: #888; text-align: center;">
                You can login later using either your email or phone number
            </p>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Validation functions
        const validateEmail = (email) => {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        };
        
        const validatePhone = (phone) => {
            const phoneRegex = /^[6-9]\d{9}$/;  // Indian phone: starts with 6-9, exactly 10 digits
            return phoneRegex.test(phone);
        };
        
        // Style focus states and add validation
        const inputs = modalContent.querySelectorAll('input');
        inputs.forEach(input => {
            input.addEventListener('focus', () => input.style.borderColor = '#667eea');
            input.addEventListener('blur', () => input.style.borderColor = '#e5e5e5');
        });
        
        // Real-time email validation
        const emailInput = document.getElementById('loginEmail');
        const emailError = document.getElementById('emailError');
        emailInput.addEventListener('blur', () => {
            const email = emailInput.value.trim();
            if (email && !validateEmail(email)) {
                emailError.style.display = 'block';
                emailInput.style.borderColor = '#ef4444';
            } else {
                emailError.style.display = 'none';
                emailInput.style.borderColor = '#e5e5e5';
            }
        });
        
        // Real-time phone validation (only allow digits)
        const phoneInput = document.getElementById('loginPhone');
        const phoneError = document.getElementById('phoneError');
        phoneInput.addEventListener('input', (e) => {
            // Remove non-digits
            e.target.value = e.target.value.replace(/\D/g, '').slice(0, 10);
        });
        phoneInput.addEventListener('blur', () => {
            const phone = phoneInput.value.trim();
            if (phone && !validatePhone(phone)) {
                phoneError.style.display = 'block';
                phoneInput.style.borderColor = '#ef4444';
            } else {
                phoneError.style.display = 'none';
                phoneInput.style.borderColor = '#e5e5e5';
            }
        });
        
        // Gender selection styling
        const genderLabels = ['genderMaleLabel', 'genderFemaleLabel', 'genderKidLabel'];
        const genderRadios = document.querySelectorAll('input[name="loginGender"]');
        const genderError = document.getElementById('genderError');
        
        const updateGenderStyles = () => {
            genderLabels.forEach(labelId => {
                const label = document.getElementById(labelId);
                const radio = label.querySelector('input[type="radio"]');
                if (radio.checked) {
                    label.style.borderColor = '#667eea';
                    label.style.background = 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)';
                    label.style.transform = 'scale(1.02)';
                } else {
                    label.style.borderColor = '#e5e5e5';
                    label.style.background = 'white';
                    label.style.transform = 'scale(1)';
                }
            });
            genderError.style.display = 'none';
        };
        
        genderRadios.forEach(radio => {
            radio.addEventListener('change', updateGenderStyles);
        });
        
        // Hover effects for gender labels
        genderLabels.forEach(labelId => {
            const label = document.getElementById(labelId);
            label.addEventListener('mouseenter', () => {
                if (!label.querySelector('input').checked) {
                    label.style.borderColor = '#667eea';
                }
            });
            label.addEventListener('mouseleave', () => {
                if (!label.querySelector('input').checked) {
                    label.style.borderColor = '#e5e5e5';
                }
            });
        });
        
        // Close modal
        document.getElementById('closeLoginModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Send verification code
        document.getElementById('sendLoginCode').onclick = () => {
            const email = document.getElementById('loginEmail').value.trim();
            const phone = document.getElementById('loginPhone').value.trim();
            
            if (!email || !validateEmail(email)) {
                this.showNotification('Please enter a valid email address', 'error');
                return;
            }
            if (!phone || !validatePhone(phone)) {
                this.showNotification('Please enter a valid 10-digit phone number', 'error');
                return;
            }
            this.sendVerificationCode(email, phone);
        };
        
        // Submit form
        document.getElementById('loginForm').onsubmit = (e) => {
            e.preventDefault();
            const name = document.getElementById('loginName').value.trim();
            const email = document.getElementById('loginEmail').value.trim();
            const phone = document.getElementById('loginPhone').value.trim();
            const code = document.getElementById('loginCode').value.trim();
            const genderRadio = document.querySelector('input[name="loginGender"]:checked');
            const gender = genderRadio ? genderRadio.value : null;
            
            // Validate all fields
            if (!validateEmail(email)) {
                this.showNotification('Please enter a valid email address', 'error');
                return;
            }
            if (!validatePhone(phone)) {
                this.showNotification('Please enter a valid 10-digit phone number', 'error');
                return;
            }
            if (!gender) {
                genderError.style.display = 'block';
                this.showNotification('Please select who you\'re shopping for', 'error');
                return;
            }
            
            if (this.verifyEmail(email, code)) {
                // Store user info
                this.userName = name;
                this.userPhone = phone;
                this.userGender = gender;
                sessionStorage.setItem('userName', name);
                sessionStorage.setItem('userPhone', phone);
                sessionStorage.setItem('userGender', gender);
                
                // Sync with backend
                fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email, name, phone, gender})
                }).catch(err => console.error('Login sync error:', err));
                
                modal.remove();
                this.updateUserButtonDisplay();
                this.showNotification(`Welcome, ${name}!`, 'success');
            } else {
                this.showNotification('Invalid verification code', 'error');
            }
        };
    }
    
    showAccountModal() {
        const modal = document.createElement('div');
        modal.id = 'accountModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10001';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '32px';
        modalContent.style.maxWidth = '400px';
        modalContent.style.width = '90%';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        const displayName = this.userName || this.verifiedEmail.split('@')[0];
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                <h2 style="margin: 0; color: #1a1a1a; font-size: 1.5rem;">
                    <i class="fas fa-user-circle" style="color: #10b981; margin-right: 10px;"></i>
                    My Account
                </h2>
                <button id="closeAccountModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; margin-bottom: 24px; color: white;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="width: 50px; height: 50px; background: rgba(255,255,255,0.2); border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px;">
                        <i class="fas fa-user"></i>
                    </div>
                    <div>
                        <div style="font-size: 1.1rem; font-weight: 700;">${displayName}</div>
                        <div style="font-size: 0.85rem; opacity: 0.9;">${this.verifiedEmail}</div>
                    </div>
                </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 12px;">
                <button id="viewHistoryBtn" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #f8f9fa; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">
                    <i class="fas fa-history" style="color: #667eea; font-size: 18px;"></i>
                    <span>Purchase History</span>
                    <i class="fas fa-chevron-right" style="margin-left: auto; color: #888;"></i>
                </button>
                <button id="viewPrebooksBtn" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #f8f9fa; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">
                    <i class="fas fa-bookmark" style="color: #f59e0b; font-size: 18px;"></i>
                    <span>Prebooked Orders</span>
                    <i class="fas fa-chevron-right" style="margin-left: auto; color: #888;"></i>
                </button>
                <button id="viewCartBtn" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #f8f9fa; border: 2px solid #e5e5e5; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s;">
                    <i class="fas fa-shopping-cart" style="color: #10b981; font-size: 18px;"></i>
                    <span>My Cart (${this.cart.length})</span>
                    <i class="fas fa-chevron-right" style="margin-left: auto; color: #888;"></i>
                </button>
                <button id="logoutBtn" style="display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: #fef2f2; border: 2px solid #fecaca; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 500; color: #dc2626; transition: all 0.2s; margin-top: 8px;">
                    <i class="fas fa-sign-out-alt" style="font-size: 18px;"></i>
                    <span>Logout</span>
                </button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Hover effects for buttons
        const buttons = modalContent.querySelectorAll('button[id$="Btn"]');
        buttons.forEach(btn => {
            if (btn.id !== 'logoutBtn') {
                btn.onmouseenter = () => { btn.style.borderColor = '#667eea'; btn.style.background = '#f0f4ff'; };
                btn.onmouseleave = () => { btn.style.borderColor = '#e5e5e5'; btn.style.background = '#f8f9fa'; };
            }
        });
        
        // Close modal
        document.getElementById('closeAccountModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // View history
        document.getElementById('viewHistoryBtn').onclick = () => {
            modal.remove();
            this.showPurchaseHistory();
        };
        
        // View prebooked orders
        document.getElementById('viewPrebooksBtn').onclick = () => {
            modal.remove();
            this.showPrebookHistory();
        };
        
        // View cart
        document.getElementById('viewCartBtn').onclick = () => {
            modal.remove();
            this.showCartModal();
        };
        
        // Logout
        document.getElementById('logoutBtn').onclick = () => {
            this.logout();
            modal.remove();
        };
    }
    
    logout() {
        this.verifiedEmail = null;
        this.verificationTimestamp = null;
        this.userName = null;
        sessionStorage.removeItem('verifiedEmail');
        sessionStorage.removeItem('verificationTimestamp');
        sessionStorage.removeItem('userName');
        
        // Notify backend
        fetch('/api/logout', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        }).catch(err => console.error('Logout error:', err));
        
        this.updateUserButtonDisplay();
        this.showNotification('Logged out successfully', 'info');
    }
    
    initializeQuestionSuggestions() {
        const suggestionChips = document.querySelectorAll('.suggestion-chip');
        suggestionChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const question = chip.getAttribute('data-question');
                if (question && this.messageInput) {
                    this.messageInput.value = question;
                    this.sendMessage();
                }
            });
        });
    }
    
    checkSessionValidity() {
        if (this.verificationTimestamp) {
            const now = Date.now();
            const sessionAge = now - parseInt(this.verificationTimestamp);
            const sessionTimeout = 24 * 60 * 60 * 1000; // 24 hours
            
            if (sessionAge > sessionTimeout) {
                // Session expired
                this.verifiedEmail = null;
                this.verificationTimestamp = null;
                sessionStorage.removeItem('verifiedEmail');
                sessionStorage.removeItem('verificationTimestamp');
                console.log('Session expired - verification required');
                return false;
            }
            return true;
        }
        return false;
    }
    
    initializeCartButton() {
        if (this.cartButton) {
            this.cartButton.addEventListener('click', () => {
                this.showCartModal();
            });
        }
    }
    
    updateCartDisplay() {
        const cartCount = this.cart.length;
        if (this.cartBadge) {
            this.cartBadge.textContent = cartCount;
        }
        if (this.cartButton) {
            if (cartCount > 0) {
                this.cartButton.style.display = 'flex';
            } else {
                this.cartButton.style.display = 'none';
            }
        }
    }
    
    initializeAutoScroll() {
        // Use MutationObserver to auto-scroll when new content is added
        if (this.chatMessages && 'MutationObserver' in window) {
            const observer = new MutationObserver(() => {
                // Only auto-scroll if user is near the bottom (within 100px)
                const isNearBottom = this.chatWindow ? 
                    (this.chatWindow.scrollHeight - this.chatWindow.scrollTop - this.chatWindow.clientHeight < 100) :
                    true;
                
                if (isNearBottom) {
                    this.scrollToBottom();
                }
            });
            
            observer.observe(this.chatMessages, {
                childList: true,
                subtree: true
            });
        }
    }
    
    initializeEventListeners() {
        // Verify elements exist before attaching listeners
        if (!this.sendButton) {
            console.error('❌ sendButton not found!');
            this.sendButton = document.getElementById('sendButton');
        }
        if (!this.messageInput) {
            console.error('❌ messageInput not found!');
            this.messageInput = document.getElementById('messageInput');
        }
        if (!this.clearButton) {
            console.error('❌ clearButton not found!');
            this.clearButton = document.getElementById('clearButton');
        }
        
        // Send message on button click
        if (this.sendButton) {
            this.sendButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('Send button clicked');
                this.sendMessage();
            });
            console.log('✅ Send button listener attached');
        } else {
            console.error('❌ Cannot attach send button listener - element not found');
        }
        
        // Send message on Enter key
        if (this.messageInput) {
            this.messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('Enter key pressed');
                    this.sendMessage();
                }
            });
            console.log('✅ Enter key listener attached');
        } else {
            console.error('❌ Cannot attach Enter key listener - element not found');
        }
        
        // Clear chat
        if (this.clearButton) {
            this.clearButton.addEventListener('click', () => this.clearChat());
        }
        
        // Voice button
        if (this.voiceButton) {
            this.voiceButton.addEventListener('click', () => this.toggleVoiceRecognition());
        }
        
        // Auto-resize textarea (if it's a textarea, not needed for input)
        if (this.messageInput && this.messageInput.tagName === 'TEXTAREA') {
            this.messageInput.addEventListener('input', () => {
                this.messageInput.style.height = 'auto';
                this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
            });
        }
    }
    
    initializeSocketListeners() {
        // Bot response
        this.socket.on('bot_response', (data) => {
            console.log('✅ Received bot_response event:', data); // Debug log
            console.log('✅ Socket connected:', this.socket.connected); // Debug log
            console.log('✅ Socket ID:', this.socket.id); // Debug log
            
            // Use setTimeout to ensure DOM is ready
            setTimeout(() => {
                try {
                    // Hide skeleton loader first
                    console.log('Hiding skeleton loader...');
                    this.hideSkeletonLoader();
                    
                    if (data.error) {
                        console.error('Bot response error:', data.error);
                        this.addMessage('bot', `❌ Error: ${data.error}`);
                    } else {
                        console.log('Adding bot message - Message:', data.message?.substring(0, 100), 'Images:', data.images?.length || 0);
                        if (data.message) {
                            const messageAdded = this.addMessage('bot', data.message, data.images || []);
                            // Auto-speak bot response only if input was from voice
                            if (this.lastInputWasVoice) {
                                this.speakText(data.message);
                            }
                            // Reset flag after processing response
                            this.lastInputWasVoice = false;
                            if (messageAdded) {
                                console.log('✅ Message added successfully');
                            } else {
                                console.error('❌ addMessage returned false');
                                // Force show message as fallback
                                this.forceAddMessage('bot', data.message, data.images || []);
                            }
                            
                            // Handle special actions from backend
                            if (data.action === 'open_cart') {
                                // Auto-open cart modal after a brief delay
                                setTimeout(() => {
                                    this.showCartModal();
                                }, 500);
                            }
                        } else {
                            console.error('❌ No message in bot response data:', data);
                            this.addMessage('bot', 'I received your message but had trouble generating a response. Please try again.');
                        }
                    }
                } catch (error) {
                    console.error('❌ Error handling bot response:', error);
                    console.error('Error stack:', error.stack);
                    this.hideSkeletonLoader();
                    // Try to show error message
                    try {
                        this.addMessage('bot', `❌ Error: ${error.message}`);
                    } catch (e) {
                        console.error('Failed to add error message:', e);
                        // Last resort - directly manipulate DOM
                        if (this.chatMessages) {
                            const errorDiv = document.createElement('div');
                            errorDiv.className = 'message bot';
                            errorDiv.innerHTML = `<div class="message-avatar"><i class="fas fa-shopping-bag"></i></div><div class="message-content"><p>❌ Error: ${error.message}</p></div>`;
                            this.chatMessages.appendChild(errorDiv);
                            this.scrollToBottom();
                        }
                    }
                }
            }, 10); // Small delay to ensure DOM is ready
        });
        
        // Bot typing indicator
        this.socket.on('bot_typing', (data) => {
            if (data.typing) {
                this.showSkeletonLoader();
            }
        });
    }
    
    sendMessage() {
        console.log('sendMessage called, isLoading:', this.isLoading);
        console.log('messageInput:', this.messageInput);
        
        if (!this.messageInput) {
            console.error('❌ messageInput not found in sendMessage');
            this.messageInput = document.getElementById('messageInput');
            if (!this.messageInput) {
                console.error('❌ Still cannot find messageInput');
                return;
            }
        }
        
        const message = this.messageInput.value.trim();
        console.log('Message value:', message);
        
        if (!message) {
            console.log('❌ Empty message, not sending');
            return;
        }
        
        if (this.isLoading) {
            console.log('❌ Already loading, not sending');
            return;
        }
        
        // If sendMessage is called directly (not from voice), mark as text input
        // Note: voice input will set lastInputWasVoice=true before calling sendMessage
        if (!this.lastInputWasVoice) {
            this.lastInputWasVoice = false; // Explicitly set to false for text input
        }
        
        // Set loading state
        this.isLoading = true;
        if (this.sendButton) {
            this.sendButton.disabled = true;
        }
        
        console.log('✅ Sending message:', message);
        
        this.addMessage('user', message);
        this.chatHistory.push({ role: 'user', content: message });
        
        // Show skeleton loader immediately
        this.showSkeletonLoader();
        
        this.socket.emit('send_message', { message });
        this.messageInput.value = '';
        if (this.messageInput.tagName === 'TEXTAREA') {
            this.messageInput.style.height = 'auto';
        }
        
        // Re-enable after a short delay (will be disabled again when response comes)
        setTimeout(() => {
            if (this.sendButton) {
                this.sendButton.disabled = false;
            }
        }, 100);
    }
    
    clearChat() {
        this.chatHistory = [];
        this.cart = [];
        sessionStorage.setItem('cart', JSON.stringify(this.cart));
        this.updateCartDisplay();
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="bot-avatar">
                    <i class="fas fa-shopping-bag"></i>
                </div>
                <div class="message-content">
                    <p>Hello! I'm here to help you find the perfect Shop Assist products. What are you looking for today?</p>
                </div>
            </div>
        `;
        this.scrollToBottom();
    }
    
    addMessage(role, content, images = []) {
        console.log('addMessage called:', role, content?.substring(0, 50), 'images:', images?.length); // Debug
        console.log('chatMessages element:', this.chatMessages); // Debug
        
        if (!this.chatMessages) {
            console.error('❌ chatMessages element not found! Trying to find it...');
            this.chatMessages = document.getElementById('chatMessages');
            if (!this.chatMessages) {
                console.error('❌ Still cannot find chatMessages element!');
                return false;
            }
        }
        
        if (!content) {
            console.error('❌ No content provided to addMessage');
            return false;
        }
        
        console.log('✅ All checks passed, creating message element...');
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (role === 'user') {
            avatar.innerHTML = '<i class="fas fa-user"></i>';
            messageContent.innerHTML = `<p>${this.escapeHtml(content)}</p>`;
        } else {
            avatar.innerHTML = '<i class="fas fa-shopping-bag"></i>';
            messageContent.innerHTML = `<p>${this.formatBotMessage(content)}</p>`;
            
            // Add product images if available
            if (images && images.length > 0) {
                const imagesContainer = document.createElement('div');
                imagesContainer.className = 'product-images';
                imagesContainer.style.display = 'grid';
                
                // Responsive grid: single column on mobile, multi-column on desktop
                const isMobile = window.innerWidth <= 768;
                if (isMobile) {
                    imagesContainer.style.gridTemplateColumns = '1fr';
                } else {
                    imagesContainer.style.gridTemplateColumns = 'repeat(auto-fill, minmax(220px, 1fr))';
                }
                
                imagesContainer.style.gap = '12px';
                imagesContainer.style.marginTop = '12px';
                imagesContainer.style.maxWidth = '100%';
                
                images.forEach(imageData => {
                    const imageCard = document.createElement('div');
                    imageCard.className = 'product-image-card';
                    imageCard.style.border = '1px solid #e0e0e0';
                    imageCard.style.borderRadius = '8px';
                    imageCard.style.overflow = 'hidden';
                    imageCard.style.backgroundColor = '#fff';
                    imageCard.style.boxShadow = '0 2px 4px rgba(0,0,0,0.08)';
                    imageCard.style.transition = 'transform 0.2s, box-shadow 0.2s';
                    imageCard.style.cursor = 'pointer';
                    
                    // Responsive max-width
                    if (isMobile) {
                        imageCard.style.maxWidth = '100%';
                        imageCard.style.width = '100%';
                    } else {
                        imageCard.style.maxWidth = '240px';
                    }
                    
                    // Hover effect (only on non-touch devices)
                    if (!isMobile || window.matchMedia('(hover: hover)').matches) {
                        imageCard.onmouseenter = () => {
                            imageCard.style.transform = 'translateY(-2px)';
                            imageCard.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
                        };
                        imageCard.onmouseleave = () => {
                            imageCard.style.transform = 'translateY(0)';
                            imageCard.style.boxShadow = '0 2px 4px rgba(0,0,0,0.08)';
                        };
                    }
                    
                    // Touch-friendly tap effect for mobile
                    if (isMobile) {
                        imageCard.style.webkitTapHighlightColor = 'transparent';
                    }
                    
                    // Product Image - only show if URL exists
                    if (imageData.url && imageData.url.trim() && imageData.url !== 'N/A') {
                        const img = document.createElement('img');
                        img.src = imageData.url;
                        img.alt = imageData.product_name || 'Product image';
                        img.style.width = '100%';
                        // Responsive image height
                        if (isMobile) {
                            img.style.height = '200px';
                        } else {
                            img.style.height = '180px';
                        }
                        img.style.objectFit = 'contain';
                        img.style.objectPosition = 'center';
                        img.style.display = 'block';
                        img.style.backgroundColor = '#f5f5f5';
                        img.style.padding = '6px';
                        img.style.boxSizing = 'border-box';
                        
                        // Handle image load error - show placeholder
                        img.onerror = () => {
                            img.style.display = 'none';
                        };
                        
                        imageCard.appendChild(img);
                    } else {
                        // No image - show placeholder
                        const placeholder = document.createElement('div');
                        placeholder.style.width = '100%';
                        placeholder.style.height = isMobile ? '120px' : '100px';
                        placeholder.style.backgroundColor = '#f0f0f0';
                        placeholder.style.display = 'flex';
                        placeholder.style.alignItems = 'center';
                        placeholder.style.justifyContent = 'center';
                        placeholder.style.color = '#999';
                        placeholder.style.fontSize = '12px';
                        placeholder.innerHTML = '🛍️ No Image';
                        imageCard.appendChild(placeholder);
                    }
                    
                    // Product Info Container
                    const infoDiv = document.createElement('div');
                    // Responsive padding
                    if (isMobile) {
                        infoDiv.style.padding = '12px';
                    } else {
                        infoDiv.style.padding = '10px';
                    }
                    
                    // Product Name
                    if (imageData.product_name) {
                        const nameP = document.createElement('h3');
                        nameP.style.margin = '0 0 6px 0';
                        nameP.style.fontSize = '14px';
                        nameP.style.fontWeight = '600';
                        nameP.style.color = '#1a1a1a';
                        nameP.style.lineHeight = '1.3';
                        nameP.style.display = '-webkit-box';
                        nameP.style.webkitLineClamp = '2';
                        nameP.style.webkitBoxOrient = 'vertical';
                        nameP.style.overflow = 'hidden';
                        nameP.style.textOverflow = 'ellipsis';
                        nameP.textContent = imageData.product_name;
                        infoDiv.appendChild(nameP);
                    }
                    
                    // Description - cleaned and beautified
                    if (imageData.description && imageData.description.trim()) {
                        // Further clean description on frontend (remove any remaining noise)
                        let cleanDesc = imageData.description.trim();
                        
                        // Remove any remaining price patterns
                        cleanDesc = cleanDesc.replace(/₹[\d,]+\.?\d*/g, '');
                        cleanDesc = cleanDesc.replace(/\d+%\s*OFF/gi, '');
                        
                        // Remove any remaining button/action text
                        cleanDesc = cleanDesc.replace(/Buy now|Add to Bag|ADD TO WISHLIST/gi, '');
                        
                        // Remove extra whitespace
                        cleanDesc = cleanDesc.replace(/\s+/g, ' ').trim();
                        
                        // Only show if it's meaningful (at least 30 chars and looks like a description)
                        if (cleanDesc.length >= 30 && !cleanDesc.match(/^(Material|Fit|Style|Code|Brand|Size|Color):/i)) {
                            const descP = document.createElement('p');
                            descP.style.margin = '0 0 8px 0';
                            descP.style.fontSize = '11px';
                            descP.style.color = '#666';
                            descP.style.lineHeight = '1.4';
                            descP.style.display = '-webkit-box';
                            descP.style.webkitLineClamp = '2'; // Show up to 2 lines
                            descP.style.webkitBoxOrient = 'vertical';
                            descP.style.overflow = 'hidden';
                            descP.style.textOverflow = 'ellipsis';
                            descP.textContent = cleanDesc;
                            infoDiv.appendChild(descP);
                        }
                    }
                    
                    // Category & Subcategory
                    if (imageData.category || imageData.subcategory) {
                        const categoryDiv = document.createElement('div');
                        categoryDiv.style.marginBottom = '6px';
                        categoryDiv.style.fontSize = '10px';
                        categoryDiv.style.color = '#888';
                        const categoryText = [imageData.category, imageData.subcategory].filter(Boolean).join(' • ');
                        categoryDiv.textContent = categoryText;
                        infoDiv.appendChild(categoryDiv);
                    }
                    
                    // Details Row (Size, Color, Material) - Compact single line
                    const details = [];
                    if (imageData.size) details.push(`Size: ${imageData.size}`);
                    if (imageData.color) details.push(`Color: ${imageData.color}`);
                    if (imageData.material) details.push(`Material: ${imageData.material}`);
                    
                    if (details.length > 0) {
                        const detailsDiv = document.createElement('div');
                        detailsDiv.style.marginBottom = '6px';
                        detailsDiv.style.fontSize = '10px';
                        detailsDiv.style.color = '#555';
                        detailsDiv.style.lineHeight = '1.4';
                        detailsDiv.innerHTML = details.join(' • ');
                        infoDiv.appendChild(detailsDiv);
                    }
                    
                    // Price - Beautified display
                    if (imageData.discounted_price || imageData.base_price) {
                        const priceContainer = document.createElement('div');
                        priceContainer.style.marginBottom = '8px';
                        
                        // Main price (discounted or base)
                        const mainPriceDiv = document.createElement('div');
                        mainPriceDiv.style.display = 'flex';
                        mainPriceDiv.style.alignItems = 'center';
                        mainPriceDiv.style.gap = '6px';
                        mainPriceDiv.style.flexWrap = 'wrap';
                        
                        try {
                            const discounted = parseFloat(imageData.discounted_price);
                            const base = parseFloat(imageData.base_price);
                            const discountPct = parseFloat(imageData.discount_percent);
                            
                            // Current price (discounted if available, otherwise base)
                            const currentPrice = discounted && discounted < base ? discounted : base;
                            const hasDiscount = discounted && base && discounted < base && discountPct > 0;
                            
                            // Display current price
                            const priceSpan = document.createElement('span');
                            priceSpan.style.fontSize = '16px';
                            priceSpan.style.fontWeight = '700';
                            priceSpan.style.color = '#2563eb';
                            priceSpan.textContent = `₹${currentPrice.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
                            mainPriceDiv.appendChild(priceSpan);
                            
                            // If there's a discount, show original price and discount badge
                            if (hasDiscount) {
                                // Original price with strikethrough
                                const originalPriceSpan = document.createElement('span');
                                originalPriceSpan.style.fontSize = '11px';
                                originalPriceSpan.style.color = '#888';
                                originalPriceSpan.style.textDecoration = 'line-through';
                                originalPriceSpan.textContent = `₹${base.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
                                mainPriceDiv.appendChild(originalPriceSpan);
                                
                                // Discount badge
                                const discountBadge = document.createElement('span');
                                discountBadge.style.fontSize = '9px';
                                discountBadge.style.fontWeight = '600';
                                discountBadge.style.color = '#fff';
                                discountBadge.style.backgroundColor = '#dc2626';
                                discountBadge.style.padding = '1px 5px';
                                discountBadge.style.borderRadius = '3px';
                                discountBadge.textContent = `${Math.round(discountPct)}% OFF`;
                                mainPriceDiv.appendChild(discountBadge);
                            }
                        } catch (e) {
                            // Fallback to simple price display if parsing fails
                            const priceSpan = document.createElement('span');
                            priceSpan.style.fontSize = '16px';
                            priceSpan.style.fontWeight = '700';
                            priceSpan.style.color = '#2563eb';
                            priceSpan.textContent = imageData.price || `₹${imageData.base_price || ''}`;
                            mainPriceDiv.appendChild(priceSpan);
                        }
                        
                        priceContainer.appendChild(mainPriceDiv);
                        infoDiv.appendChild(priceContainer);
                    } else if (imageData.price) {
                        // Fallback if only price string is available
                        const priceDiv = document.createElement('div');
                        priceDiv.style.marginBottom = '8px';
                        priceDiv.style.fontSize = '16px';
                        priceDiv.style.fontWeight = '700';
                        priceDiv.style.color = '#2563eb';
                        priceDiv.textContent = imageData.price;
                        infoDiv.appendChild(priceDiv);
                    }
                    
                    // Availability & Stock Status
                    if (imageData.availability || imageData.stock_status) {
                        const availabilityDiv = document.createElement('div');
                        availabilityDiv.style.marginBottom = '6px';
                        availabilityDiv.style.fontSize = '10px';
                        const status = imageData.stock_status || imageData.availability;
                        if (status && status.toLowerCase().includes('stock')) {
                            availabilityDiv.style.color = '#059669';
                            availabilityDiv.style.fontWeight = '600';
                        } else {
                            availabilityDiv.style.color = '#dc2626';
                        }
                        availabilityDiv.textContent = status || imageData.availability;
                        infoDiv.appendChild(availabilityDiv);
                    }
                    
                    // Store Location
                    if (imageData.store_name || imageData.store_location) {
                        const storeDiv = document.createElement('div');
                        storeDiv.style.marginTop = '6px';
                        storeDiv.style.paddingTop = '6px';
                        storeDiv.style.borderTop = '1px solid #e5e5e5';
                        storeDiv.style.fontSize = '9px';
                        storeDiv.style.color = '#888';
                        const storeText = [imageData.store_name, imageData.store_location].filter(Boolean).join(', ');
                        storeDiv.style.display = '-webkit-box';
                        storeDiv.style.webkitLineClamp = '1';
                        storeDiv.style.webkitBoxOrient = 'vertical';
                        storeDiv.style.overflow = 'hidden';
                        storeDiv.style.textOverflow = 'ellipsis';
                        storeDiv.textContent = `📍 ${storeText}`;
                        infoDiv.appendChild(storeDiv);
                    }
                    
                    // Check if this is a purchase history item - show order details above action buttons
                    if (imageData.is_purchase_history) {
                        // Add Order Details section to the card content (above buttons)
                        const orderDetailsDiv = document.createElement('div');
                        orderDetailsDiv.style.marginTop = '8px';
                        orderDetailsDiv.style.padding = '8px';
                        orderDetailsDiv.style.backgroundColor = '#f0fdf4';
                        orderDetailsDiv.style.borderRadius = '6px';
                        orderDetailsDiv.style.fontSize = '11px';
                        // Check if prebook or purchase and set appropriate colors
                        const isPrebook = imageData.order_type === 'prebook';
                        orderDetailsDiv.style.backgroundColor = isPrebook ? '#fef3c7' : '#f0fdf4';
                        orderDetailsDiv.style.color = isPrebook ? '#92400e' : '#166534';
                        
                        // Format order date
                        let orderDateStr = '';
                        if (imageData.order_date) {
                            try {
                                const orderDate = new Date(imageData.order_date);
                                orderDateStr = orderDate.toLocaleDateString('en-IN', { 
                                    day: 'numeric', 
                                    month: 'short', 
                                    year: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                });
                            } catch(e) {
                                orderDateStr = imageData.order_date;
                            }
                        }
                        
                        // Order type tag
                        const orderTypeTag = isPrebook 
                            ? '<span style="display: inline-block; background: #f59e0b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 8px;">📝 PREBOOKED</span>'
                            : '<span style="display: inline-block; background: #059669; color: white; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 8px;">🛒 PURCHASED</span>';
                        
                        let orderDetailsHTML = `<div style="font-weight: 600; margin-bottom: 4px; color: ${isPrebook ? '#b45309' : '#15803d'};">📦 Order Details ${orderTypeTag}</div>`;
                        
                        if (orderDateStr) {
                            orderDetailsHTML += `<div>📅 <strong>${isPrebook ? 'Booked:' : 'Ordered:'}</strong> ${orderDateStr}</div>`;
                        }
                        
                        if (isPrebook) {
                            // Prebook - show pickup location
                            if (imageData.pickup_location || imageData.store_location) {
                                orderDetailsHTML += `<div style="margin-top: 3px;">🏪 <strong>Pickup from:</strong> ${imageData.pickup_location || imageData.store_location}</div>`;
                            }
                            if (imageData.store_name) {
                                orderDetailsHTML += `<div style="margin-top: 3px;">🏬 <strong>Store:</strong> ${imageData.store_name}</div>`;
                            }
                        } else {
                            // Purchase - show shipping address and payment
                            if (imageData.shipping_address) {
                                orderDetailsHTML += `<div style="margin-top: 3px;">📍 <strong>Shipped to:</strong> ${imageData.shipping_address}</div>`;
                            }
                            if (imageData.payment_method) {
                                orderDetailsHTML += `<div style="margin-top: 3px;">💳 <strong>Payment:</strong> ${imageData.payment_method.toUpperCase()}</div>`;
                            }
                        }
                        
                        orderDetailsDiv.innerHTML = orderDetailsHTML;
                        infoDiv.appendChild(orderDetailsDiv);
                    }
                    
                    // Action Buttons Container - always at the bottom
                    const actionsDiv = document.createElement('div');
                    actionsDiv.style.marginTop = '8px';
                    actionsDiv.style.paddingTop = '8px';
                    actionsDiv.style.borderTop = '1px solid #e5e5e5';
                    actionsDiv.style.display = 'flex';
                    actionsDiv.style.gap = '6px';
                    actionsDiv.style.flexWrap = 'wrap';
                    
                    if (imageData.is_purchase_history) {
                        // Buy Again button for purchase history
                        const buyAgainBtn = document.createElement('button');
                        buyAgainBtn.textContent = '🔄 Buy Again';
                        buyAgainBtn.style.width = '100%';
                        buyAgainBtn.style.padding = '10px 12px';
                        buyAgainBtn.style.backgroundColor = '#7c3aed';
                        buyAgainBtn.style.color = 'white';
                        buyAgainBtn.style.border = 'none';
                        buyAgainBtn.style.borderRadius = '6px';
                        buyAgainBtn.style.cursor = 'pointer';
                        buyAgainBtn.style.fontSize = '12px';
                        buyAgainBtn.style.fontWeight = '600';
                        buyAgainBtn.style.transition = 'background-color 0.2s';
                        buyAgainBtn.onmouseenter = () => buyAgainBtn.style.backgroundColor = '#6d28d9';
                        buyAgainBtn.onmouseleave = () => buyAgainBtn.style.backgroundColor = '#7c3aed';
                        buyAgainBtn.onclick = () => this.showBuyAgainModal(imageData);
                        actionsDiv.appendChild(buyAgainBtn);
                    } else {
                        // Regular product - show Offline and Online buttons
                        // Shop Offline Button
                        if (imageData.store_location || imageData.google_maps_link) {
                            const shopOfflineBtn = document.createElement('button');
                            shopOfflineBtn.textContent = '🛍️ Offline';
                            shopOfflineBtn.style.flex = '1';
                            shopOfflineBtn.style.minWidth = '90px';
                            shopOfflineBtn.style.padding = '6px 10px';
                            shopOfflineBtn.style.backgroundColor = '#2563eb';
                            shopOfflineBtn.style.color = 'white';
                            shopOfflineBtn.style.border = 'none';
                            shopOfflineBtn.style.borderRadius = '6px';
                            shopOfflineBtn.style.cursor = 'pointer';
                            shopOfflineBtn.style.fontSize = '11px';
                            shopOfflineBtn.style.fontWeight = '600';
                            shopOfflineBtn.style.transition = 'background-color 0.2s';
                            shopOfflineBtn.onmouseenter = () => shopOfflineBtn.style.backgroundColor = '#1d4ed8';
                            shopOfflineBtn.onmouseleave = () => shopOfflineBtn.style.backgroundColor = '#2563eb';
                            shopOfflineBtn.onclick = () => this.showShopOfflineModal(imageData);
                            actionsDiv.appendChild(shopOfflineBtn);
                        }
                        
                        // Shop Online Button
                        const shopOnlineBtn = document.createElement('button');
                        shopOnlineBtn.textContent = '🛒 Online';
                        shopOnlineBtn.style.flex = '1';
                        shopOnlineBtn.style.minWidth = '90px';
                        shopOnlineBtn.style.padding = '6px 10px';
                        shopOnlineBtn.style.backgroundColor = '#059669';
                        shopOnlineBtn.style.color = 'white';
                        shopOnlineBtn.style.border = 'none';
                        shopOnlineBtn.style.borderRadius = '6px';
                        shopOnlineBtn.style.cursor = 'pointer';
                        shopOnlineBtn.style.fontSize = '11px';
                        shopOnlineBtn.style.fontWeight = '600';
                        shopOnlineBtn.style.transition = 'background-color 0.2s';
                        shopOnlineBtn.onmouseenter = () => shopOnlineBtn.style.backgroundColor = '#047857';
                        shopOnlineBtn.onmouseleave = () => shopOnlineBtn.style.backgroundColor = '#059669';
                        shopOnlineBtn.onclick = () => this.showShopOnlineModal(imageData);
                        actionsDiv.appendChild(shopOnlineBtn);
                    }
                    
                    infoDiv.appendChild(actionsDiv);
                    
                    // Image already appended above in the image handling block
                    imageCard.appendChild(infoDiv);
                    imagesContainer.appendChild(imageCard);
                });
                
                messageContent.appendChild(imagesContainer);
            }
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        try {
            this.chatMessages.appendChild(messageDiv);
            console.log('✅ Message appended to DOM'); // Debug
            
            // Scroll immediately
            this.scrollToBottom();
            
            // If images are present, wait for them to load and scroll again
            if (images && images.length > 0) {
                // Wait for all images to potentially load
                const imagesInMessage = messageDiv.querySelectorAll('img');
                let loadedCount = 0;
                const totalImages = imagesInMessage.length;
                
                if (totalImages > 0) {
                    imagesInMessage.forEach(img => {
                        if (img.complete) {
                            loadedCount++;
                        } else {
                            img.addEventListener('load', () => {
                                loadedCount++;
                                if (loadedCount === totalImages) {
                                    this.scrollToBottom();
                                }
                            }, { once: true });
                        }
                    });
                }
                
                // If all images are already loaded
                if (loadedCount === totalImages) {
                    setTimeout(() => this.scrollToBottom(), 100);
                }
            }
            
            // Add to chat history
            if (role === 'bot') {
                this.chatHistory.push({ role: 'assistant', content, images });
            }
            
            return true;
        } catch (error) {
            console.error('❌ Error appending message to DOM:', error);
            return false;
        }
    }
    
    forceAddMessage(role, content, images = []) {
        // Fallback method to force add message if regular method fails
        console.log('forceAddMessage called as fallback');
        try {
            if (!this.chatMessages) {
                this.chatMessages = document.getElementById('chatMessages');
            }
            if (!this.chatMessages) {
                console.error('❌ Cannot find chatMessages in forceAddMessage');
                return false;
            }
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = `
                <div class="message-avatar">
                    ${role === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-shopping-bag"></i>'}
                </div>
                <div class="message-content">
                    <p>${this.escapeHtml(content)}</p>
                </div>
            `;
            this.chatMessages.appendChild(messageDiv);
            this.scrollToBottom();
            return true;
        } catch (error) {
            console.error('❌ Error in forceAddMessage:', error);
            return false;
        }
    }
    
    formatBotMessage(content) {
        // Format the bot message with proper line breaks and styling
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showSkeletonLoader() {
        this.isLoading = true;
        if (this.sendButton) {
            this.sendButton.disabled = true;
        }
        
        // Remove existing skeleton if any
        if (this.skeletonMessage) {
            this.skeletonMessage.remove();
        }
        
        // Create skeleton message
        const skeletonDiv = document.createElement('div');
        skeletonDiv.className = 'message bot skeleton-message';
        skeletonDiv.id = 'skeleton-loader';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-shopping-bag"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content skeleton-content';
        
        // Create skeleton lines
        const skeletonLines = [
            { width: '90%', height: '16px' },
            { width: '75%', height: '16px' },
            { width: '60%', height: '16px' }
        ];
        
        skeletonLines.forEach((line, index) => {
            const lineDiv = document.createElement('div');
            lineDiv.className = 'skeleton-line';
            lineDiv.style.width = line.width;
            lineDiv.style.height = line.height;
            lineDiv.style.marginBottom = index < skeletonLines.length - 1 ? '12px' : '0';
            lineDiv.style.borderRadius = '4px';
            lineDiv.style.backgroundColor = '#e0e0e0';
            lineDiv.style.animation = 'skeleton-pulse 1.5s ease-in-out infinite';
            lineDiv.style.animationDelay = `${index * 0.2}s`;
            messageContent.appendChild(lineDiv);
        });
        
        skeletonDiv.appendChild(avatar);
        skeletonDiv.appendChild(messageContent);
        
        // Append to chat
        if (this.chatMessages) {
            this.chatMessages.appendChild(skeletonDiv);
            this.skeletonMessage = skeletonDiv;
            this.scrollToBottom();
        }
    }
    
    hideSkeletonLoader() {
        console.log('hideSkeletonLoader called');
        this.isLoading = false;
        if (this.sendButton) {
            this.sendButton.disabled = false;
            console.log('✅ Send button re-enabled');
        }
        
        // Remove skeleton message by reference
        if (this.skeletonMessage) {
            try {
                console.log('Removing skeleton by reference');
                this.skeletonMessage.remove();
                this.skeletonMessage = null;
            } catch (e) {
                console.error('Error removing skeleton by reference:', e);
            }
        }
        
        // Also try to remove by ID as fallback
        const skeletonById = document.getElementById('skeleton-loader');
        if (skeletonById) {
            try {
                console.log('Removing skeleton by ID');
                skeletonById.remove();
            } catch (e) {
                console.error('Error removing skeleton by ID:', e);
            }
        }
        
        // Also try to remove by class name as additional fallback
        const skeletonByClass = document.querySelector('.skeleton-message');
        if (skeletonByClass) {
            try {
                console.log('Removing skeleton by class');
                skeletonByClass.remove();
            } catch (e) {
                console.error('Error removing skeleton by class:', e);
            }
        }
        
        console.log('Skeleton loader hidden');
    }
    
    showLoading() {
        // Legacy method - keeping for compatibility
        this.showSkeletonLoader();
    }
    
    hideLoading() {
        // Legacy method - keeping for compatibility
        this.hideSkeletonLoader();
    }
    
    scrollToBottom() {
        // Use multiple methods to ensure scroll happens after all content is loaded
        const scroll = () => {
            // Try scrolling the chat window (scrollable container)
            if (this.chatWindow) {
                this.chatWindow.scrollTop = this.chatWindow.scrollHeight;
            }
            // Fallback to chat messages if chatWindow doesn't work
            if (this.chatMessages) {
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
        };
        
        // Immediate scroll
        scroll();
        
        // Scroll after a short delay (for DOM updates)
        setTimeout(scroll, 50);
        
        // Scroll after images might have loaded
        setTimeout(scroll, 200);
        
        // Scroll after longer delay (for slow image loads)
        setTimeout(scroll, 500);
        
        // Use requestAnimationFrame for smooth scroll (double RAF for layout recalculation)
        requestAnimationFrame(() => {
            requestAnimationFrame(scroll);
        });
    }
    
    // Shopping Modal Functions
    showShopOfflineModal(productData) {
        const modal = document.createElement('div');
        modal.id = 'shopOfflineModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10000';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '600px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        // Construct proper Google Maps URLs
        const storeLocation = productData.store_location || productData.store_name || '';
        const mapsSearchLink = productData.google_maps_link || 
            `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(storeLocation)}`;
        
        // Use Google Maps search URL - this will work in iframe for most cases
        // If the link contains place ID, use it; otherwise use search query
        let mapsEmbedUrl = mapsSearchLink;
        if (mapsSearchLink.includes('/place/')) {
            // Extract place ID from URL if present
            const placeMatch = mapsSearchLink.match(/\/place\/([^/]+)/);
            if (placeMatch) {
                mapsEmbedUrl = `https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3806.1234567890!2d78.4567890!3d17.1234567!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMTfCsDA3JzI0LjQiTiA3OMKwMjcnMjQuNCJF!5e0!3m2!1sen!2sin!4v1234567890123!5m2!1sen!2sin`;
            }
        }
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">🛍️ Shop Offline</h2>
                <button id="closeOfflineModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">${productData.product_name || 'Product'}</h3>
                <p style="color: #666; margin: 5px 0;">${productData.price || ''}</p>
            </div>
            <div style="margin-bottom: 20px;">
                <p style="color: #333; margin-bottom: 10px;"><strong>📍 Store Location:</strong></p>
                <p style="color: #666; margin: 5px 0;">${productData.store_name || ''}</p>
                <p style="color: #666; margin: 5px 0;">${productData.store_location || ''}</p>
            </div>
            <div style="margin-bottom: 20px; height: 300px; border-radius: 8px; overflow: hidden; background: #f0f0f0; position: relative;">
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; flex-direction: column; padding: 20px; box-sizing: border-box;">
                    <div style="font-size: 48px; margin-bottom: 10px;">📍</div>
                    <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px; text-align: center;">${productData.store_name || 'Store Location'}</div>
                    <div style="font-size: 14px; text-align: center; opacity: 0.9;">${productData.store_location || ''}</div>
                    <div style="margin-top: 20px; font-size: 12px; opacity: 0.8; text-align: center;">Click "Get Directions" to navigate to this store</div>
                </div>
            </div>
            <div style="background: #f0f9ff; padding: 16px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #1e40af; line-height: 1.6;">
                    <strong>💡 Visit our store to purchase this product!</strong><br>
                    You can also prebook this product to ensure availability.
                </p>
            </div>
            <div style="display: flex; gap: 10px;">
                <button id="openMapsBtn" style="flex: 1; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    🧭 Get Directions
                </button>
                <button id="prebookBtn" style="flex: 1; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    📝 Prebook Product
                </button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close modal
        document.getElementById('closeOfflineModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Open Maps with Directions
        document.getElementById('openMapsBtn').onclick = () => {
            const destinationAddress = storeLocation;
            const openMapsBtn = document.getElementById('openMapsBtn');
            
            // Show loading state
            openMapsBtn.innerHTML = '⏳ Getting your location...';
            openMapsBtn.disabled = true;
            
            // Try to get user's current location for directions
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        // Success - open directions from user's location to store
                        const userLat = position.coords.latitude;
                        const userLng = position.coords.longitude;
                        const directionsUrl = `https://www.google.com/maps/dir/?api=1&origin=${userLat},${userLng}&destination=${encodeURIComponent(destinationAddress)}&travelmode=driving`;
                        window.open(directionsUrl, '_blank');
                        openMapsBtn.innerHTML = '🧭 Get Directions';
                        openMapsBtn.disabled = false;
                    },
                    (error) => {
                        // Location denied or error - open with just destination (user can set origin manually)
                        console.log('Geolocation error:', error.message);
                        const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destinationAddress)}&travelmode=driving`;
                        window.open(directionsUrl, '_blank');
                        openMapsBtn.innerHTML = '🧭 Get Directions';
                        openMapsBtn.disabled = false;
                    },
                    {
                        enableHighAccuracy: true,
                        timeout: 10000,
                        maximumAge: 300000 // Cache location for 5 minutes
                    }
                );
            } else {
                // Geolocation not supported - open directions without origin
                const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(destinationAddress)}&travelmode=driving`;
                window.open(directionsUrl, '_blank');
            }
        };
        
        // Prebook
        document.getElementById('prebookBtn').onclick = () => {
            modal.remove();
            this.showPrebookModal(productData);
        };
    }
    
    showBuyAgainModal(productData) {
        const modal = document.createElement('div');
        modal.id = 'buyAgainModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10000';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '450px';
        modalContent.style.width = '90%';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        const price = productData.discounted_price || productData.base_price || productData.price || '';
        const imageUrl = productData.url || '';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">🔄 Buy Again</h2>
                <button id="closeBuyAgainModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="display: flex; gap: 15px; margin-bottom: 20px; padding: 16px; background: #f9fafb; border-radius: 12px;">
                <img src="${imageUrl}" alt="${productData.product_name || ''}" style="width: 80px; height: 80px; object-fit: contain; background: #fff; border-radius: 8px; flex-shrink: 0;">
                <div style="flex: 1;">
                    <h3 style="margin: 0 0 8px 0; color: #333; font-size: 15px;">${productData.product_name || 'Product'}</h3>
                    <p style="margin: 0 0 4px 0; color: #666; font-size: 13px;">${productData.color || ''}${productData.color && productData.size ? ' • ' : ''}${productData.size || ''}</p>
                    <p style="margin: 0; font-size: 16px; font-weight: 600; color: #2563eb;">${typeof price === 'string' && price.includes('₹') ? price : '₹' + price}</p>
                </div>
            </div>
            <p style="text-align: center; color: #666; margin-bottom: 20px; font-size: 14px;">How would you like to purchase?</p>
            <div style="display: flex; gap: 12px;">
                <button id="buyAgainOfflineBtn" style="flex: 1; padding: 14px; background: #2563eb; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 14px;">
                    🛍️ Shop Offline
                </button>
                <button id="buyAgainOnlineBtn" style="flex: 1; padding: 14px; background: #059669; color: white; border: none; border-radius: 10px; cursor: pointer; font-weight: 600; font-size: 14px;">
                    🛒 Shop Online
                </button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        document.getElementById('closeBuyAgainModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        document.getElementById('buyAgainOfflineBtn').onclick = () => {
            modal.remove();
            this.showShopOfflineModal(productData);
        };
        
        document.getElementById('buyAgainOnlineBtn').onclick = () => {
            modal.remove();
            this.showShopOnlineModal(productData);
        };
    }
    
    showShopOnlineModal(productData) {
        const modal = document.createElement('div');
        modal.id = 'shopOnlineModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10000';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '500px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">🛒 Shop Online</h2>
                <button id="closeOnlineModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="margin-bottom: 20px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">${productData.product_name || 'Product'}</h3>
                <p style="color: #666; margin: 5px 0; font-size: 18px; font-weight: 600; color: #2563eb;">${productData.price || ''}</p>
            </div>
            <div style="display: flex; gap: 10px;">
                <button id="addToCartBtn" style="flex: 1; padding: 12px; background: #f59e0b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    🛒 Add to Cart
                </button>
                <button id="purchaseNowBtn" style="flex: 1; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    💳 Purchase Now
                </button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close modal
        document.getElementById('closeOnlineModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Add to Cart
        document.getElementById('addToCartBtn').onclick = () => {
            this.addToCart(productData);
            modal.remove();
            this.showNotification('Product added to cart!', 'success');
        };
        
        // Purchase Now
        document.getElementById('purchaseNowBtn').onclick = () => {
            modal.remove();
            this.showPurchaseModal(productData);
        };
    }
    
    addToCart(productData) {
        this.cart.push({
            ...productData,
            added_at: new Date().toISOString()
        });
        sessionStorage.setItem('cart', JSON.stringify(this.cart));
        this.updateCartDisplay();
        
        // Also sync with backend
        fetch('/api/cart', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({product: productData})
        }).catch(err => console.error('Cart sync error:', err));
        
        console.log('Cart updated:', this.cart);
    }
    
    showPrebookModal(productData) {
        // Check if already verified - skip to form directly
        if (this.isVerified()) {
            this.showPrebookForm(productData, this.verifiedEmail);
        } else {
            this.showEmailVerificationModal('prebook', productData);
        }
    }
    
    showPurchaseModal(productData) {
        // Check if already verified - skip to form directly
        if (this.isVerified()) {
            this.showPurchaseForm(productData, this.verifiedEmail);
        } else {
            this.showEmailVerificationModal('purchase', productData);
        }
    }
    
    showEmailVerificationModal(action, productData) {
        const modal = document.createElement('div');
        modal.id = 'emailVerificationModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10001';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '500px';
        modalContent.style.width = '90%';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">📧 Email Verification</h2>
                <button id="closeEmailModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <form id="emailVerificationForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Email Address *</label>
                    <input type="email" id="userEmail" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Verification Code *</label>
                    <input type="text" id="verificationCode" required placeholder="Enter 6-digit code" maxlength="6" style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                    <button type="button" id="sendCodeBtn" style="margin-top: 8px; padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px;">
                        Send Verification Code
                    </button>
                </div>
                <button type="submit" style="width: 100%; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 16px;">
                    Verify & Continue
                </button>
            </form>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close modal
        document.getElementById('closeEmailModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Send verification code
        document.getElementById('sendCodeBtn').onclick = () => {
            const email = document.getElementById('userEmail').value;
            if (email) {
                this.sendVerificationCode(email);
            } else {
                alert('Please enter your email address first');
            }
        };
        
        // Submit form
        document.getElementById('emailVerificationForm').onsubmit = (e) => {
            e.preventDefault();
            const email = document.getElementById('userEmail').value;
            const code = document.getElementById('verificationCode').value;
            
            if (this.verifyEmail(email, code)) {
                modal.remove();
                if (action === 'prebook') {
                    this.showPrebookForm(productData, email);
                } else if (action === 'cart') {
                    this.showCartModal();
                } else if (action === 'history') {
                    this.showPurchaseHistory();
                } else {
                    this.showPurchaseForm(productData, email);
                }
            } else {
                alert('Invalid verification code. Please try again.');
            }
        };
    }
    
    sendVerificationCode(email, phone = null) {
        // In production, this would send an actual OTP via email/SMS
        // For demo, generate a random 6-digit code
        const code = Math.floor(100000 + Math.random() * 900000).toString();
        console.log(`Verification code for ${email}${phone ? ` / ${phone}` : ''}: ${code}`);
        
        let message = `Demo: Verification code sent!\n\nCode: ${code}\n\n`;
        if (phone) {
            message += `📧 Email: ${email}\n📱 Phone: +91 ${phone}\n\n`;
            message += `(In production, OTP would be sent via SMS/Email)`;
        } else {
            message += `📧 Email: ${email}\n\n`;
            message += `(In production, this would be sent via email)`;
        }
        
        alert(message);
        
        // Store code for both email and phone lookup
        sessionStorage.setItem(`verification_${email}`, code);
        if (phone) {
            sessionStorage.setItem(`verification_${phone}`, code);
        }
    }
    
    verifyEmail(email, code) {
        const storedCode = sessionStorage.getItem(`verification_${email}`);
        if (storedCode === code) {
            // Store verified email and timestamp
            this.verifiedEmail = email;
            this.verificationTimestamp = Date.now().toString();
            sessionStorage.setItem('verifiedEmail', email);
            sessionStorage.setItem('verificationTimestamp', this.verificationTimestamp);
            
            // Notify backend
            fetch('/api/verify', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email: email, verified: true})
            }).catch(err => console.error('Verification sync error:', err));
            
            return true;
        }
        return false;
    }
    
    isVerified() {
        return this.verifiedEmail !== null && this.checkSessionValidity();
    }
    
    showCartModal() {
        // Check if user is verified
        if (!this.isVerified()) {
            this.showEmailVerificationModal('cart', null);
            return;
        }
        
        const modal = document.createElement('div');
        modal.id = 'cartModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10002';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '600px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        if (this.cart.length === 0) {
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">🛒 Shopping Cart</h2>
                    <button id="closeCartModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="text-align: center; padding: 40px 20px;">
                    <i class="fas fa-shopping-cart" style="font-size: 48px; color: #ccc; margin-bottom: 20px;"></i>
                    <p style="color: #666; font-size: 18px;">Your cart is empty</p>
                </div>
            `;
        } else {
            let cartItemsHTML = '';
            let total = 0;
            
            this.cart.forEach((item, index) => {
                const price = parseFloat(item.discounted_price || item.base_price || 0);
                total += price;
                
                cartItemsHTML += `
                    <div style="display: flex; gap: 15px; padding: 15px; border-bottom: 1px solid #e5e5e5; align-items: center;">
                        <img src="${item.url || ''}" alt="${item.product_name || ''}" style="width: 80px; height: 80px; object-fit: contain; background: #f5f5f5; border-radius: 8px;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 5px 0; font-size: 14px; color: #333;">${item.product_name || 'Product'}</h4>
                            <p style="margin: 0; font-size: 12px; color: #666;">${item.color || ''} ${item.size || ''}</p>
                            <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: 700; color: #2563eb;">₹${price.toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</p>
                        </div>
                        <button class="removeCartItem" data-index="${index}" style="background: #dc2626; color: white; border: none; border-radius: 50%; width: 30px; height: 30px; cursor: pointer; font-size: 14px;">&times;</button>
                    </div>
                `;
            });
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">🛒 Shopping Cart (${this.cart.length})</h2>
                    <button id="closeCartModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="max-height: 400px; overflow-y: auto; margin-bottom: 20px;">
                    ${cartItemsHTML}
                </div>
                <div style="border-top: 2px solid #e5e5e5; padding-top: 15px; margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <span style="font-size: 18px; font-weight: 600;">Total:</span>
                        <span style="font-size: 24px; font-weight: 700; color: #2563eb;">₹${total.toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</span>
                    </div>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <button id="viewWishlistBtn" style="flex: 1; min-width: 120px; padding: 12px; background: #f59e0b; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        💛 Wishlist
                    </button>
                    <button id="viewHistoryBtn" style="flex: 1; min-width: 120px; padding: 12px; background: #6c757d; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        📜 History
                    </button>
                    <button id="checkoutBtn" style="flex: 2; min-width: 150px; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        💳 Checkout
                    </button>
                </div>
            `;
        }
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close modal
        document.getElementById('closeCartModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Remove item handlers
        modalContent.querySelectorAll('.removeCartItem').forEach(btn => {
            btn.onclick = (e) => {
                const index = parseInt(e.target.getAttribute('data-index'));
                this.cart.splice(index, 1);
                sessionStorage.setItem('cart', JSON.stringify(this.cart));
                this.updateCartDisplay();
                modal.remove();
                this.showCartModal(); // Refresh modal
            };
        });
        
        // View wishlist button
        const wishlistBtn = modalContent.querySelector('#viewWishlistBtn');
        if (wishlistBtn) {
            wishlistBtn.onclick = () => {
                modal.remove();
                this.showWishlistModal();
            };
        }
        
        // View history button
        const historyBtn = modalContent.querySelector('#viewHistoryBtn');
        if (historyBtn) {
            historyBtn.onclick = () => {
                modal.remove();
                this.showPurchaseHistory();
            };
        }
        
        // Checkout button
        const checkoutBtn = modalContent.querySelector('#checkoutBtn');
        if (checkoutBtn) {
            checkoutBtn.onclick = () => {
                modal.remove();
                this.showCheckoutModal();
            };
        }
    }
    
    showWishlistModal() {
        if (!this.isVerified()) {
            this.showNotification('Please login to view your wishlist', 'warning');
            this.showEmailVerificationModal('wishlist', null);
            return;
        }
        
        // Fetch wishlist from backend
        fetch('/api/wishlist')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    this.displayWishlist(data.wishlist || []);
                } else {
                    if (data.error && data.error.includes('login')) {
                        this.showNotification('Please login to view wishlist', 'warning');
                    } else {
                        this.showNotification('Failed to load wishlist', 'error');
                    }
                }
            })
            .catch(err => {
                console.error('Wishlist error:', err);
                this.showNotification('Error loading wishlist', 'error');
            });
    }
    
    displayWishlist(wishlist) {
        const modal = document.createElement('div');
        modal.id = 'wishlistModal';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); display: flex; align-items: center;
            justify-content: center; z-index: 10003;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white; border-radius: 16px; padding: 24px;
            max-width: 700px; width: 90%; max-height: 90vh; overflow: auto;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        `;
        
        if (wishlist.length === 0) {
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">💛 My Wishlist</h2>
                    <button id="closeWishlistModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="text-align: center; padding: 40px 20px;">
                    <i class="fas fa-heart" style="font-size: 48px; color: #fbbf24; margin-bottom: 20px;"></i>
                    <p style="color: #666; font-size: 18px;">Your wishlist is empty</p>
                    <p style="color: #999; font-size: 14px;">Save items here to buy later!</p>
                </div>
            `;
        } else {
            let wishlistHTML = wishlist.map((item, index) => {
                let imageUrl = item.url || item.image_url || '';
                if (imageUrl && imageUrl.startsWith('data/')) {
                    imageUrl = '/static/' + imageUrl.replace('data/', '');
                }
                const price = parseFloat(item.discounted_price || item.base_price || 0);
                const addedDate = item.added_to_wishlist ? new Date(item.added_to_wishlist).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '';
                
                return `
                    <div style="display: flex; gap: 15px; padding: 15px; border-bottom: 1px solid #e5e5e5; align-items: center;">
                        <img src="${imageUrl}" alt="${item.product_name || ''}" 
                             style="width: 80px; height: 80px; object-fit: contain; background: #f5f5f5; border-radius: 8px;">
                        <div style="flex: 1; min-width: 0;">
                            <h4 style="margin: 0 0 5px 0; font-size: 14px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${item.product_name || 'Product'}</h4>
                            <p style="margin: 0; font-size: 12px; color: #666;">${item.color || ''} ${item.size || ''}</p>
                            <p style="margin: 5px 0 0 0; font-size: 16px; font-weight: 700; color: #2563eb;">₹${price.toLocaleString('en-IN')}</p>
                            ${addedDate ? `<p style="margin: 2px 0 0 0; font-size: 11px; color: #999;">Added ${addedDate}</p>` : ''}
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 8px;">
                            <button class="addToCartFromWishlist" data-product='${JSON.stringify(item).replace(/'/g, "&#39;")}'
                                    style="padding: 8px 12px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; white-space: nowrap;">
                                🛒 Add to Cart
                            </button>
                            <button class="removeFromWishlist" data-product-id="${item.product_url || item.product_name}"
                                    style="padding: 6px 10px; background: #f3f4f6; color: #666; border: none; border-radius: 6px; cursor: pointer; font-size: 11px;">
                                Remove
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">💛 My Wishlist (${wishlist.length})</h2>
                    <button id="closeWishlistModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="max-height: 500px; overflow-y: auto;">
                    ${wishlistHTML}
                </div>
            `;
        }
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Close modal
        document.getElementById('closeWishlistModal').onclick = () => modal.remove();
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
        
        // Add to cart buttons
        modalContent.querySelectorAll('.addToCartFromWishlist').forEach(btn => {
            btn.onclick = (e) => {
                const productData = JSON.parse(e.target.dataset.product.replace(/&#39;/g, "'"));
                this.addToCart(productData);
                // Optionally remove from wishlist after adding to cart
                const productId = productData.product_url || productData.product_name;
                this.removeFromWishlist(productId);
                modal.remove();
                this.showWishlistModal(); // Refresh
            };
        });
        
        // Remove from wishlist buttons
        modalContent.querySelectorAll('.removeFromWishlist').forEach(btn => {
            btn.onclick = (e) => {
                const productId = e.target.dataset.productId;
                this.removeFromWishlist(productId);
                modal.remove();
                this.showWishlistModal(); // Refresh
            };
        });
    }
    
    async removeFromWishlist(productId) {
        try {
            const response = await fetch('/api/wishlist', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId })
            });
            const result = await response.json();
            if (result.success) {
                this.showNotification('Removed from wishlist', 'success');
            }
        } catch (err) {
            console.error('Remove from wishlist error:', err);
        }
    }
    
    showPurchaseHistory() {
        if (!this.isVerified()) {
            this.showEmailVerificationModal('history', null);
            return;
        }
        
        // Fetch purchase history from backend (only purchases)
        fetch(`/api/purchase-history?email=${encodeURIComponent(this.verifiedEmail)}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    this.displayPurchaseHistory(data.purchases || []);
                } else {
                    this.showNotification('Failed to load purchase history', 'error');
                }
            })
            .catch(err => {
                console.error('Purchase history error:', err);
                this.showNotification('Error loading purchase history', 'error');
            });
    }
    
    displayPurchaseHistory(purchases) {
        const modal = document.createElement('div');
        modal.id = 'historyModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10003';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '700px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        if (purchases.length === 0) {
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">🛒 Purchase History</h2>
                    <button id="closeHistoryModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="text-align: center; padding: 40px 20px;">
                    <i class="fas fa-receipt" style="font-size: 48px; color: #ccc; margin-bottom: 20px;"></i>
                    <p style="color: #666; font-size: 18px;">No purchases yet</p>
                </div>
            `;
        } else {
            // Build HTML for purchases
            let purchasesHTML = purchases.map(purchase => {
                const date = purchase.date ? new Date(purchase.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'N/A';
                const price = purchase.price || purchase.amount || 0;
                
                // Parse product if it's a JSON string
                let product = purchase.product || {};
                if (typeof product === 'string') {
                    try {
                        product = JSON.parse(product);
                    } catch(e) {
                        product = {};
                    }
                }
                
                // Get image URL with path conversion
                let imageUrl = purchase.image_url || product.url || '';
                if (imageUrl && imageUrl.startsWith('data/')) {
                    imageUrl = '/static/' + imageUrl.replace('data/', '');
                } else if (imageUrl && !imageUrl.startsWith('/') && !imageUrl.startsWith('http')) {
                    imageUrl = '/static/images/' + imageUrl;
                }
                
                const color = purchase.color || product.color || '';
                const size = purchase.size || product.size || '';
                const paymentMethod = purchase.payment_method ? purchase.payment_method.toUpperCase() : '';
                
                return `
                    <div style="padding: 15px; border-bottom: 1px solid #e5e5e5; background: #f0fdf4; margin-bottom: 8px; border-radius: 8px;">
                        <div style="display: flex; gap: 15px; align-items: start;">
                            <img src="${imageUrl}" alt="${purchase.product_name || ''}" style="width: 70px; height: 70px; object-fit: contain; background: #fff; border-radius: 8px; flex-shrink: 0;">
                            <div style="flex: 1; min-width: 0;">
                                <h4 style="margin: 0 0 5px 0; font-size: 15px; color: #333;">${purchase.product_name || 'Product'}</h4>
                                <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">${color}${color && size ? ' • ' : ''}${size}</p>
                                <p style="margin: 0 0 4px 0; font-size: 12px; color: #888;">📅 ${date}</p>
                                <p style="margin: 0; font-size: 12px; color: #888;">💳 ${paymentMethod}${purchase.purchase_type ? ' • ' + purchase.purchase_type : ''}</p>
                                ${purchase.address ? `<p style="margin: 4px 0 0 0; font-size: 11px; color: #999;">📍 ${purchase.address}</p>` : ''}
                            </div>
                            <span style="font-size: 18px; font-weight: 700; color: #059669; flex-shrink: 0;">₹${parseFloat(price).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</span>
                        </div>
                    </div>
                `;
            }).join('');
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">🛒 Purchase History</h2>
                    <button id="closeHistoryModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="background: #dcfce7; color: #166534; padding: 8px 16px; border-radius: 8px; margin-bottom: 15px; font-size: 13px;">
                    📦 ${purchases.length} order${purchases.length > 1 ? 's' : ''} placed
                </div>
                <div style="max-height: 500px; overflow-y: auto;">
                    ${purchasesHTML}
                </div>
            `;
        }
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        document.getElementById('closeHistoryModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
    }
    
    showPrebookHistory() {
        if (!this.isVerified()) {
            this.showEmailVerificationModal('history', null);
            return;
        }
        
        // Fetch prebook history from backend
        fetch(`/api/purchase-history?email=${encodeURIComponent(this.verifiedEmail)}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    this.displayPrebookHistory(data.prebooks || []);
                } else {
                    this.showNotification('Failed to load prebook history', 'error');
                }
            })
            .catch(err => {
                console.error('Prebook history error:', err);
                this.showNotification('Error loading prebook history', 'error');
            });
    }
    
    displayPrebookHistory(prebooks) {
        const modal = document.createElement('div');
        modal.id = 'prebookHistoryModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10003';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '700px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        if (prebooks.length === 0) {
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">📝 Prebooked Orders</h2>
                    <button id="closePrebookHistoryModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="text-align: center; padding: 40px 20px;">
                    <i class="fas fa-bookmark" style="font-size: 48px; color: #ccc; margin-bottom: 20px;"></i>
                    <p style="color: #666; font-size: 18px;">No prebooked orders yet</p>
                    <p style="color: #999; font-size: 14px; margin-top: 10px;">Prebook products from nearby stores for in-store pickup!</p>
                </div>
            `;
        } else {
            // Build HTML for prebooks with images fixed
            let prebooksHTML = prebooks.map(prebook => {
                const date = prebook.date ? new Date(prebook.date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'N/A';
                
                // Parse product if it's a JSON string
                let product = prebook.product || {};
                if (typeof product === 'string') {
                    try {
                        product = JSON.parse(product);
                    } catch(e) {
                        product = {};
                    }
                }
                
                const price = prebook.price || product.discounted_price || product.base_price || 0;
                // Check all possible image fields - image_url stored directly, product.url, or Image_Path converted
                let imageUrl = prebook.image_url || product.url || product.image_url || '';
                
                // If image path starts with data/, convert to Flask static URL
                if (imageUrl && imageUrl.startsWith('data/')) {
                    imageUrl = '/static/' + imageUrl.replace('data/', '');
                } else if (imageUrl && !imageUrl.startsWith('/') && !imageUrl.startsWith('http')) {
                    imageUrl = '/static/images/' + imageUrl;
                }
                
                const productName = prebook.product_name || product.product_name || 'Product';
                const color = prebook.color || product.color || '';
                const size = prebook.size || product.size || '';
                const storeName = prebook.store_name || '';
                const storeLocation = prebook.store_location || prebook.pickup_location || '';
                
                return `
                    <div style="padding: 15px; border-bottom: 1px solid #e5e5e5; background: #fef3c7; margin-bottom: 8px; border-radius: 8px;">
                        <div style="display: flex; gap: 15px; align-items: start;">
                            <img src="${imageUrl}" alt="${productName}" style="width: 70px; height: 70px; object-fit: contain; background: #fff; border-radius: 8px; flex-shrink: 0;" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22><rect fill=%22%23f5f5f5%22 width=%22100%22 height=%22100%22/><text fill=%22%23999%22 x=%2250%22 y=%2250%22 text-anchor=%22middle%22 dy=%22.3em%22>No Image</text></svg>'">
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                                    <h4 style="margin: 0; font-size: 15px; color: #333;">${productName}</h4>
                                    <span style="background: #f59e0b; color: white; padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 600;">📝 PREBOOKED</span>
                                </div>
                                <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">${color}${color && size ? ' • ' : ''}${size}</p>
                                <p style="margin: 0 0 4px 0; font-size: 12px; color: #888;">📅 Booked: ${date}</p>
                                ${storeName ? `<p style="margin: 0 0 4px 0; font-size: 12px; color: #888;">🏬 ${storeName}</p>` : ''}
                                ${storeLocation ? `<p style="margin: 4px 0 0 0; font-size: 11px; color: #78716c;">🏪 Pickup: ${storeLocation}</p>` : ''}
                            </div>
                            <span style="font-size: 18px; font-weight: 700; color: #b45309; flex-shrink: 0;">₹${parseFloat(price).toLocaleString('en-IN', {minimumFractionDigits: 0, maximumFractionDigits: 0})}</span>
                        </div>
                    </div>
                `;
            }).join('');
            
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #1a1a1a;">📝 Prebooked Orders</h2>
                    <button id="closePrebookHistoryModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
                </div>
                <div style="background: #fef3c7; color: #92400e; padding: 8px 16px; border-radius: 8px; margin-bottom: 15px; font-size: 13px;">
                    📦 ${prebooks.length} prebook${prebooks.length > 1 ? 's' : ''} pending pickup
                </div>
                <div style="max-height: 500px; overflow-y: auto;">
                    ${prebooksHTML}
                </div>
            `;
        }
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        document.getElementById('closePrebookHistoryModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
    }
    
    showCheckoutModal() {
        if (this.cart.length === 0) {
            this.showNotification('Your cart is empty!', 'warning');
            return;
        }
        
        // Validate cart stock before proceeding
        this.validateCartStock().then(validationResult => {
            if (!validationResult.success) {
                this.showNotification('Unable to validate cart. Please try again.', 'error');
                return;
            }
            
            if (validationResult.out_of_stock_items && validationResult.out_of_stock_items.length > 0) {
                // Show out-of-stock items modal
                this.showOutOfStockModal(validationResult);
                return;
            }
            
            if (validationResult.limited_stock_items && validationResult.limited_stock_items.length > 0) {
                // Show warning but proceed
                this.showNotification('Some items have limited stock. Please complete your purchase soon!', 'warning');
            }
            
            // Check if already verified - same as showPurchaseModal
            if (this.isVerified()) {
                this.showPurchaseForm(this.cart, this.verifiedEmail);
            } else {
                this.showEmailVerificationModal('purchase', this.cart);
            }
        }).catch(err => {
            console.error('Cart validation error:', err);
            // Proceed anyway if validation fails
            if (this.isVerified()) {
                this.showPurchaseForm(this.cart, this.verifiedEmail);
            } else {
                this.showEmailVerificationModal('purchase', this.cart);
            }
        });
    }
    
    async validateCartStock() {
        try {
            const response = await fetch('/api/validate-cart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ cart: this.cart })
            });
            return await response.json();
        } catch (err) {
            console.error('Cart validation error:', err);
            return { success: false, error: err.message };
        }
    }
    
    showOutOfStockModal(validationResult) {
        const modal = document.createElement('div');
        modal.id = 'outOfStockModal';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.5); display: flex; align-items: center;
            justify-content: center; z-index: 10004;
        `;
        
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white; border-radius: 16px; padding: 24px;
            max-width: 550px; width: 90%; max-height: 80vh; overflow-y: auto;
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        `;
        
        const outOfStockItems = validationResult.out_of_stock_items || [];
        const availableItems = validationResult.available_items || [];
        
        // Build out of stock items HTML
        let outOfStockHTML = outOfStockItems.map((item, idx) => {
            let imageUrl = item.url || '';
            if (imageUrl && imageUrl.startsWith('data/')) {
                imageUrl = '/static/' + imageUrl.replace('data/', '');
            }
            return `
                <div style="display: flex; gap: 12px; padding: 12px; background: #fef2f2; border-radius: 8px; margin-bottom: 10px; align-items: center; opacity: 0.7;">
                    <img src="${imageUrl}" alt="${item.product_name || ''}" 
                         style="width: 50px; height: 50px; object-fit: contain; background: #f5f5f5; border-radius: 6px; filter: grayscale(100%);">
                    <div style="flex: 1; min-width: 0;">
                        <p style="margin: 0; color: #991b1b; font-size: 13px; font-weight: 600;">${item.product_name || 'Product'}</p>
                        <p style="margin: 4px 0 0 0; color: #dc2626; font-size: 12px; font-weight: 600;">❌ Out of Stock</p>
                    </div>
                    <button class="moveToWishlistBtn" data-index="${idx}" data-product='${JSON.stringify(item).replace(/'/g, "&#39;")}'
                            style="padding: 8px 12px; background: #f59e0b; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; white-space: nowrap;">
                        💛 Move to Wishlist
                    </button>
                </div>
            `;
        }).join('');
        
        // Build available items HTML (summary)
        let availableHTML = '';
        if (availableItems.length > 0) {
            availableHTML = `
                <div style="margin-top: 16px; padding: 12px; background: #f0fdf4; border-radius: 8px;">
                    <p style="margin: 0 0 8px 0; color: #166534; font-weight: 600;">✅ ${availableItems.length} item(s) available:</p>
                    ${availableItems.map(item => `<span style="display: inline-block; background: #dcfce7; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px; color: #15803d;">${item.product_name?.substring(0, 30) || 'Product'}...</span>`).join('')}
                </div>
            `;
        }
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #991b1b;">⚠️ Stock Alert</h2>
                <button id="closeOutOfStockModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <p style="color: #666; margin-bottom: 16px;">Some items in your cart are no longer available. Please remove them or move to wishlist to continue.</p>
            
            <h3 style="color: #991b1b; margin: 0 0 12px 0; font-size: 14px;">Out of Stock Items:</h3>
            ${outOfStockHTML}
            
            ${availableHTML}
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button id="removeAllOutOfStock" style="flex: 1; padding: 12px; background: #dc2626; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    🗑️ Remove All Out of Stock
                </button>
                <button id="continueWithAvailable" style="flex: 1; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; ${availableItems.length === 0 ? 'display: none;' : ''}">
                    ✅ Continue with Available
                </button>
            </div>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        // Event handlers
        document.getElementById('closeOutOfStockModal').onclick = () => modal.remove();
        modal.onclick = (e) => { if (e.target === modal) modal.remove(); };
        
        // Move to wishlist buttons
        modalContent.querySelectorAll('.moveToWishlistBtn').forEach(btn => {
            btn.onclick = async (e) => {
                const productData = JSON.parse(e.target.dataset.product.replace(/&#39;/g, "'"));
                await this.moveToWishlist(productData);
                // Refresh the modal
                modal.remove();
                this.validateCartStock().then(result => {
                    if (result.out_of_stock_items && result.out_of_stock_items.length > 0) {
                        this.showOutOfStockModal(result);
                    } else {
                        this.showCheckoutModal();
                    }
                });
            };
        });
        
        // Remove all out of stock
        document.getElementById('removeAllOutOfStock').onclick = () => {
            // Remove out of stock items from cart
            const outOfStockIds = outOfStockItems.map(item => item.product_url || item.product_name);
            this.cart = this.cart.filter(item => {
                const itemId = item.product_url || item.product_name;
                return !outOfStockIds.includes(itemId);
            });
            sessionStorage.setItem('cart', JSON.stringify(this.cart));
            this.updateCartDisplay();
            modal.remove();
            
            if (this.cart.length > 0) {
                this.showNotification('Out of stock items removed. You can now checkout.', 'success');
                this.showCheckoutModal();
            } else {
                this.showNotification('Cart is now empty.', 'info');
            }
        };
        
        // Continue with available items
        const continueBtn = document.getElementById('continueWithAvailable');
        if (continueBtn) {
            continueBtn.onclick = () => {
                // Remove out of stock items and proceed
                const outOfStockIds = outOfStockItems.map(item => item.product_url || item.product_name);
                this.cart = this.cart.filter(item => {
                    const itemId = item.product_url || item.product_name;
                    return !outOfStockIds.includes(itemId);
                });
                sessionStorage.setItem('cart', JSON.stringify(this.cart));
                this.updateCartDisplay();
                modal.remove();
                
                if (this.isVerified()) {
                    this.showPurchaseForm(this.cart, this.verifiedEmail);
                } else {
                    this.showEmailVerificationModal('purchase', this.cart);
                }
            };
        }
    }
    
    async moveToWishlist(product) {
        try {
            const response = await fetch('/api/move-to-wishlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product, remove_from_cart: true })
            });
            const result = await response.json();
            
            if (result.success) {
                // Update local cart
                const productId = product.product_url || product.product_name;
                this.cart = this.cart.filter(item => {
                    const itemId = item.product_url || item.product_name;
                    return itemId !== productId;
                });
                sessionStorage.setItem('cart', JSON.stringify(this.cart));
                this.updateCartDisplay();
                this.showNotification('Product moved to wishlist! 💛', 'success');
            } else {
                if (result.error && result.error.includes('login')) {
                    this.showNotification('Please login to use wishlist', 'warning');
                } else {
                    this.showNotification(result.error || 'Failed to move to wishlist', 'error');
                }
            }
        } catch (err) {
            console.error('Move to wishlist error:', err);
            this.showNotification('Error moving to wishlist', 'error');
        }
    }
    
    showPrebookForm(productData, email) {
        // Implementation for prebook form
        const modal = document.createElement('div');
        modal.id = 'prebookFormModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10002';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '500px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">📝 Prebook Product</h2>
                <button id="closePrebookModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="margin-bottom: 20px; padding: 12px; background: #f9fafb; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #333;">${productData.product_name || 'Product'}</h3>
                <p style="color: #2563eb; margin: 5px 0; font-weight: 600;">${productData.price || ''}</p>
            </div>
            <div style="margin-bottom: 16px; padding: 12px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;">
                <p style="margin: 0; color: #92400e; font-size: 13px;">
                    <strong>🏪 Pickup Location:</strong><br>
                    ${productData.store_name || 'Shop Assist Store'}<br>
                    📍 ${productData.store_location || ''}
                </p>
                <p style="margin: 8px 0 0 0; color: #78716c; font-size: 12px;">
                    <em>You will pick up the product from this store</em>
                </p>
            </div>
            <form id="prebookForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Full Name *</label>
                    <input type="text" id="prebookName" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Phone Number *</label>
                    <input type="tel" id="prebookPhone" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <button type="submit" style="width: 100%; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 16px;">
                    ✅ Confirm Prebook
                </button>
            </form>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        document.getElementById('closePrebookModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        document.getElementById('prebookForm').onsubmit = (e) => {
            e.preventDefault();
            const prebookData = {
                email: email,
                name: document.getElementById('prebookName').value,
                phone: document.getElementById('prebookPhone').value,
                pickup_location: productData.store_location,  // Store location for pickup
                product: productData,
                store_location: productData.store_location,
                store_name: productData.store_name
            };
            
            this.submitPrebook(prebookData);
            modal.remove();
        };
    }
    
    showPurchaseForm(productData, email) {
        // Handle both single product and cart (array of products)
        const isCart = Array.isArray(productData);
        const products = isCart ? productData : [productData];
        
        // Calculate total price
        let totalPrice = 0;
        products.forEach(item => {
            totalPrice += parseFloat(item.discounted_price || item.base_price || 0);
        });
        
        // Build product summary HTML with thumbnails
        let productSummaryHTML = '';
        if (isCart) {
            productSummaryHTML = products.map(item => {
                const itemPrice = parseFloat(item.discounted_price || item.base_price || 0);
                return `<div style="display: flex; gap: 12px; padding: 10px 0; border-bottom: 1px solid #eee; align-items: center;">
                    <img src="${item.url || ''}" alt="${item.product_name || ''}" style="width: 50px; height: 50px; object-fit: contain; background: #f5f5f5; border-radius: 6px; flex-shrink: 0;">
                    <div style="flex: 1; min-width: 0;">
                        <p style="margin: 0; color: #333; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${item.product_name || 'Product'}</p>
                        <p style="margin: 4px 0 0 0; color: #666; font-size: 11px;">${item.color || ''} ${item.size || ''}</p>
                    </div>
                    <span style="color: #2563eb; font-weight: 600; flex-shrink: 0;">₹${itemPrice.toLocaleString('en-IN')}</span>
                </div>`;
            }).join('') + `<div style="display: flex; justify-content: space-between; padding-top: 12px; margin-top: 8px; border-top: 2px solid #ddd;">
                <span style="font-weight: 700;">Total:</span>
                <span style="color: #2563eb; font-weight: 700; font-size: 16px;">₹${totalPrice.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
            </div>`;
        } else {
            productSummaryHTML = `
                <div style="display: flex; gap: 15px; align-items: center;">
                    <img src="${productData.url || ''}" alt="${productData.product_name || ''}" style="width: 70px; height: 70px; object-fit: contain; background: #f5f5f5; border-radius: 8px; flex-shrink: 0;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0 0 8px 0; color: #333; font-size: 15px;">${productData.product_name || 'Product'}</h3>
                        <p style="margin: 0; font-size: 18px; font-weight: 600; color: #2563eb;">₹${totalPrice.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
                    </div>
                </div>
            `;
        }
        
        const modal = document.createElement('div');
        modal.id = 'purchaseFormModal';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
        modal.style.display = 'flex';
        modal.style.alignItems = 'center';
        modal.style.justifyContent = 'center';
        modal.style.zIndex = '10002';
        
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = 'white';
        modalContent.style.borderRadius = '16px';
        modalContent.style.padding = '24px';
        modalContent.style.maxWidth = '600px';
        modalContent.style.width = '90%';
        modalContent.style.maxHeight = '90vh';
        modalContent.style.overflow = 'auto';
        modalContent.style.boxShadow = '0 20px 40px rgba(0,0,0,0.3)';
        
        modalContent.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="margin: 0; color: #1a1a1a;">💳 ${isCart ? `Checkout (${products.length} items)` : 'Purchase Now'}</h2>
                <button id="closePurchaseModal" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #666;">&times;</button>
            </div>
            <div style="margin-bottom: 20px; padding: 16px; background: #f9fafb; border-radius: 8px; max-height: 200px; overflow-y: auto;">
                ${productSummaryHTML}
            </div>
            <form id="purchaseForm">
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Full Name *</label>
                    <input type="text" id="purchaseName" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Phone Number *</label>
                    <input type="tel" id="purchasePhone" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Shipping Address *</label>
                    <textarea id="purchaseAddress" required rows="3" style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box; resize: vertical;"></textarea>
                </div>
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Payment Method *</label>
                    <select id="paymentMethod" required style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                        <option value="">Select Payment Method</option>
                        <option value="cod">Cash on Delivery (COD)</option>
                        <option value="card">Credit/Debit Card</option>
                        <option value="upi">UPI</option>
                        <option value="netbanking">Net Banking</option>
                    </select>
                </div>
                <div id="cardDetails" style="display: none; margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600;">Card Number</label>
                    <input type="text" id="cardNumber" placeholder="1234 5678 9012 3456" style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;">
                </div>
                <button type="submit" style="width: 100%; padding: 12px; background: #059669; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 16px;">
                    Place Order
                </button>
            </form>
        `;
        
        modal.appendChild(modalContent);
        document.body.appendChild(modal);
        
        document.getElementById('closePurchaseModal').onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
        
        // Show/hide card details
        document.getElementById('paymentMethod').onchange = (e) => {
            document.getElementById('cardDetails').style.display = 
                e.target.value === 'card' ? 'block' : 'none';
        };
        
        document.getElementById('purchaseForm').onsubmit = (e) => {
            e.preventDefault();
            const name = document.getElementById('purchaseName').value;
            const phone = document.getElementById('purchasePhone').value;
            const address = document.getElementById('purchaseAddress').value;
            const paymentMethod = document.getElementById('paymentMethod').value;
            
            // Submit purchase for each product
            products.forEach(item => {
                const itemPrice = item.discounted_price || item.base_price || '0';
                const purchaseData = {
                    email: email,
                    name: name,
                    phone: phone,
                    address: address,
                    product: item,
                    payment_method: paymentMethod,
                    amount: itemPrice
                };
                this.submitPurchase(purchaseData);
            });
            
            // If cart checkout, clear the cart
            if (isCart) {
                this.cart = [];
                sessionStorage.setItem('cart', JSON.stringify(this.cart));
                this.updateCartDisplay();
            }
            
            modal.remove();
        };
    }
    
    submitPrebook(prebookData) {
        // Send to backend
        fetch('/api/prebook', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(prebookData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.showNotification('Product prebooked successfully! 🎉', 'success');
            } else if (data.out_of_stock) {
                // Handle out of stock error
                this.showNotification(`Sorry! This item is out of stock. Available: ${data.available_quantity || 0}`, 'error');
                // Offer to add to wishlist
                if (prebookData.product && this.isVerified()) {
                    setTimeout(() => {
                        if (confirm('Would you like to add this item to your wishlist?')) {
                            this.moveToWishlist(prebookData.product);
                        }
                    }, 1000);
                }
            } else {
                this.showNotification(data.error || 'Failed to prebook. Please try again.', 'error');
            }
        })
        .catch(err => {
            console.error('Prebook error:', err);
            this.showNotification('Error occurred. Please try again.', 'error');
        });
    }
    
    submitPurchase(purchaseData) {
        // Send to backend
        fetch('/api/purchase', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(purchaseData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                this.showNotification('Order placed successfully! 🎉', 'success');
            } else if (data.out_of_stock) {
                // Handle out of stock error
                this.showNotification(`Sorry! This item is out of stock. Available: ${data.available_quantity || 0}`, 'error');
                // Offer to add to wishlist
                if (purchaseData.product && this.isVerified()) {
                    setTimeout(() => {
                        if (confirm('Would you like to add this item to your wishlist?')) {
                            this.moveToWishlist(purchaseData.product);
                        }
                    }, 1000);
                }
            } else {
                this.showNotification(data.error || 'Failed to place order. Please try again.', 'error');
            }
        })
        .catch(err => {
            console.error('Purchase error:', err);
            this.showNotification('Error occurred. Please try again.', 'error');
        });
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.style.position = 'fixed';
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.padding = '16px 24px';
        notification.style.borderRadius = '8px';
        notification.style.color = 'white';
        notification.style.fontWeight = '600';
        notification.style.zIndex = '10003';
        notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.2)';
        
        if (type === 'success') {
            notification.style.backgroundColor = '#059669';
        } else if (type === 'error') {
            notification.style.backgroundColor = '#dc2626';
        } else {
            notification.style.backgroundColor = '#2563eb';
        }
        
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Initialize the app when DOM is loaded
let chatAppInstance = null;

function initializeApp() {
    if (!chatAppInstance) {
        console.log('Initializing ChatApp...');
        chatAppInstance = new ChatApp();
        console.log('✅ ChatApp initialized');
    } else {
        console.log('ChatApp already initialized');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    // DOM is already loaded
    initializeApp();
}

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        // Page is visible, refresh connection if needed
        console.log('Page is visible');
    }
});

// Handle window resize - update product card layouts
let resizeTimeout;
window.addEventListener('resize', () => {
    // Debounce resize handler
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Update all product image containers to match new screen size
        const productContainers = document.querySelectorAll('.product-images');
        const isMobile = window.innerWidth <= 768;
        
        productContainers.forEach(container => {
            if (isMobile) {
                container.style.gridTemplateColumns = '1fr';
            } else {
                container.style.gridTemplateColumns = 'repeat(auto-fill, minmax(220px, 1fr))';
            }
        });
        
        // Update all product cards
        const productCards = document.querySelectorAll('.product-image-card');
        productCards.forEach(card => {
            if (isMobile) {
                card.style.maxWidth = '100%';
                card.style.width = '100%';
            } else {
                card.style.maxWidth = '240px';
            }
        });
        
        console.log('Layout updated for screen size:', window.innerWidth);
    }, 150);
});

// Voice Assistance Methods
ChatApp.prototype.initVoiceRecognition = function() {
    // Check browser support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        console.warn('⚠️ Speech Recognition not supported in this browser');
        if (this.voiceButton) {
            this.voiceButton.style.display = 'none';
        }
        return;
    }
    
    // Initialize recognition
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = 'en-US';
    
    // Recognition events
    this.recognition.onstart = () => {
        this.isListening = true;
        this.updateVoiceButton(true);
        this.showVoiceStatus('Listening...');
        console.log('🎤 Voice recognition started');
    };
    
    this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        console.log('🎤 Voice input:', transcript);
        
        if (this.messageInput) {
            this.messageInput.value = transcript;
            // Mark that this input is from voice
            this.lastInputWasVoice = true;
            // Auto-send after voice input
            setTimeout(() => {
                this.sendMessage();
            }, 300);
        }
    };
    
    this.recognition.onerror = (event) => {
        console.error('❌ Voice recognition error:', event.error);
        let errorMsg = 'Voice recognition error';
        
        if (event.error === 'no-speech') {
            errorMsg = 'No speech detected. Try again.';
        } else if (event.error === 'audio-capture') {
            errorMsg = 'Microphone not found. Please check your microphone.';
        } else if (event.error === 'not-allowed') {
            errorMsg = 'Microphone permission denied. Please allow microphone access.';
        }
        
        this.showVoiceStatus(errorMsg, true);
        setTimeout(() => {
            this.hideVoiceStatus();
        }, 3000);
    };
    
    this.recognition.onend = () => {
        this.isListening = false;
        this.updateVoiceButton(false);
        this.hideVoiceStatus();
        console.log('🎤 Voice recognition ended');
    };
};

ChatApp.prototype.toggleVoiceRecognition = function() {
    if (!this.recognition) {
        alert('Voice recognition is not supported in your browser. Please use Chrome, Edge, or Safari.');
        return;
    }
    
    if (this.isListening) {
        this.recognition.stop();
    } else {
        try {
            this.recognition.start();
        } catch (error) {
            console.error('❌ Failed to start recognition:', error);
            if (error.message && error.message.includes('already started')) {
                // Recognition already running, just stop and restart
                this.recognition.stop();
                setTimeout(() => {
                    this.recognition.start();
                }, 100);
            }
        }
    }
};

ChatApp.prototype.updateVoiceButton = function(isListening) {
    if (!this.voiceButton) return;
    
    const icon = this.voiceButton.querySelector('i');
    if (icon) {
        if (isListening) {
            icon.className = 'fas fa-microphone-slash';
            this.voiceButton.classList.add('listening');
        } else {
            icon.className = 'fas fa-microphone';
            this.voiceButton.classList.remove('listening');
        }
    }
};

ChatApp.prototype.showVoiceStatus = function(text, isError) {
    if (!this.voiceStatus || !this.voiceStatusText) return;
    
    this.voiceStatusText.textContent = text;
    this.voiceStatus.style.display = 'flex';
    
    if (isError) {
        this.voiceStatus.classList.add('error');
    } else {
        this.voiceStatus.classList.remove('error');
    }
};

ChatApp.prototype.hideVoiceStatus = function() {
    if (this.voiceStatus) {
        this.voiceStatus.style.display = 'none';
    }
};

ChatApp.prototype.speakText = function(text) {
    // Check if TTS is supported
    if (!this.synthesis) {
        console.warn('⚠️ Text-to-Speech not supported');
        return;
    }
    
    // Stop any ongoing speech
    if (this.isSpeaking) {
        this.synthesis.cancel();
    }
    
    // Clean text (remove emojis, special characters that might cause issues)
    const cleanText = text
        .replace(/[^\w\s.,!?;:()\-]/g, '') // Remove special chars except basic punctuation
        .replace(/\s+/g, ' ') // Normalize whitespace
        .trim();
    
    if (!cleanText || cleanText.length < 3) {
        return; // Skip very short or empty text
    }
    
    // Create speech utterance
    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang = 'en-US';
    utterance.rate = 1.0; // Normal speed
    utterance.pitch = 1.0; // Normal pitch
    utterance.volume = 0.8; // 80% volume
    
    utterance.onstart = () => {
        this.isSpeaking = true;
        console.log('🔊 Speaking:', cleanText.substring(0, 50));
    };
    
    utterance.onend = () => {
        this.isSpeaking = false;
        console.log('🔊 Finished speaking');
    };
    
    utterance.onerror = (event) => {
        this.isSpeaking = false;
        console.error('❌ Speech synthesis error:', event.error);
    };
    
    // Speak
    this.synthesis.speak(utterance);
};

ChatApp.prototype.stopSpeaking = function() {
    if (this.synthesis && this.isSpeaking) {
        this.synthesis.cancel();
        this.isSpeaking = false;
    }
};
