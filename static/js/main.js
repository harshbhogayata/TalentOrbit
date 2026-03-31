/* =============================================
   TalentOrbit — Main JavaScript
   ============================================= */

document.addEventListener('DOMContentLoaded', () => {
    const root = document.documentElement;

    // ── Scroll Reveal (Intersection Observer) ──────
    const revealElements = document.querySelectorAll('[data-animate]');
    if (revealElements.length) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const delay = entry.target.dataset.delay || 0;
                    setTimeout(() => {
                        entry.target.classList.add('revealed');
                    }, parseInt(delay));
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

        revealElements.forEach(el => observer.observe(el));
    }


    // ── Navbar Scroll Effect ───────────────────────
    const navbar = document.getElementById('mainNav');
    if (navbar) {
        const syncNavOffset = () => {
            const navHeight = Math.ceil(navbar.getBoundingClientRect().height);
            root.style.setProperty('--nav-offset', `${navHeight}px`);
            root.style.setProperty('--dashboard-nav-offset', `${navHeight}px`);
        };

        const onScroll = () => {
            if (window.scrollY > 50) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        };
        syncNavOffset();
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', syncNavOffset, { passive: true });
        window.addEventListener('load', syncNavOffset, { once: true });
        const mobileNavPanel = document.getElementById('mobileNavPanel');
        if (mobileNavPanel) {
            mobileNavPanel.addEventListener('shown.bs.collapse', syncNavOffset);
            mobileNavPanel.addEventListener('hidden.bs.collapse', syncNavOffset);
        }
        onScroll();
    }


    // ── Back to Top Button ─────────────────────────
    // —— Dashboard Sidebar Drawer ————————————————————————————————
    const dashboardSidebar = document.getElementById('dashboardSidebar');
    const dashboardSidebarToggle = document.querySelector('[data-dashboard-sidebar-toggle]');
    const dashboardSidebarBackdrop = document.querySelector('[data-dashboard-sidebar-backdrop]');
    const dashboardSidebarClose = document.querySelector('[data-dashboard-sidebar-close]');

    if (dashboardSidebar && dashboardSidebarToggle) {
        const mobileSidebarMedia = window.matchMedia('(max-width: 992px)');

        const setDashboardSidebarOpen = (isOpen) => {
            if (!mobileSidebarMedia.matches) {
                document.body.classList.remove('dashboard-sidebar-open');
                dashboardSidebarToggle.setAttribute('aria-expanded', 'false');
                if (dashboardSidebarBackdrop) dashboardSidebarBackdrop.hidden = true;
                return;
            }

            document.body.classList.toggle('dashboard-sidebar-open', isOpen);
            dashboardSidebarToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');

            if (dashboardSidebarBackdrop) {
                dashboardSidebarBackdrop.hidden = !isOpen;
            }
        };

        dashboardSidebarToggle.addEventListener('click', () => {
            const nextOpenState = !document.body.classList.contains('dashboard-sidebar-open');
            setDashboardSidebarOpen(nextOpenState);
        });

        if (dashboardSidebarBackdrop) {
            dashboardSidebarBackdrop.addEventListener('click', () => setDashboardSidebarOpen(false));
        }

        if (dashboardSidebarClose) {
            dashboardSidebarClose.addEventListener('click', () => setDashboardSidebarOpen(false));
        }

        dashboardSidebar.addEventListener('click', (event) => {
            if (!mobileSidebarMedia.matches) return;
            if (event.target.closest('.dash-nav-link')) {
                setDashboardSidebarOpen(false);
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && document.body.classList.contains('dashboard-sidebar-open')) {
                setDashboardSidebarOpen(false);
            }
        });

        mobileSidebarMedia.addEventListener('change', () => {
            setDashboardSidebarOpen(false);
        });
    }


    const backToTop = document.getElementById('backToTop');
    if (backToTop) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 400) {
                backToTop.classList.add('visible');
            } else {
                backToTop.classList.remove('visible');
            }
        }, { passive: true });

        backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }


    // ── Toast Notification System ──────────────────
    const toastContainer = document.getElementById('toastContainer');

    window.showToast = function(type, message, duration = 5000) {
        if (!toastContainer) return;

        const iconMap = {
            success: 'bi-check-circle-fill',
            danger: 'bi-exclamation-circle-fill',
            error: 'bi-exclamation-circle-fill',
            warning: 'bi-exclamation-triangle-fill',
            info: 'bi-info-circle-fill'
        };

        const toast = document.createElement('div');
        toast.className = `toast-item toast-${escapeHtml(type)}`;

        const icon = document.createElement('i');
        icon.className = `bi ${iconMap[type] || iconMap.info} toast-icon`;

        const body = document.createElement('div');
        body.className = 'toast-body';
        body.textContent = message;

        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', 'Close');
        closeBtn.innerHTML = '&times;';

        const progress = document.createElement('div');
        progress.className = 'toast-progress';
        progress.style.width = '100%';

        toast.appendChild(icon);
        toast.appendChild(body);
        toast.appendChild(closeBtn);
        toast.appendChild(progress);

        toastContainer.appendChild(toast);

        // Animate progress bar
        requestAnimationFrame(() => {
            progress.style.transitionDuration = duration + 'ms';
            progress.style.width = '0%';
        });

        const removeToast = () => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        };

        closeBtn.addEventListener('click', removeToast);
        setTimeout(removeToast, duration);
    };

    // Auto-show Django messages as toasts
    const djangoMessages = document.querySelectorAll('[data-toast-type]');
    djangoMessages.forEach((msg, i) => {
        setTimeout(() => {
            showToast(msg.dataset.toastType, msg.dataset.toastMessage);
        }, i * 200);
    });




    // ── Search Autocomplete ────────────────────────
    const searchInput = document.getElementById('heroSearchInput');
    const suggestionsBox = document.getElementById('heroSearchSuggestions');
    let debounceTimer;
    let activeIndex = -1;

    if (searchInput && suggestionsBox) {
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const q = searchInput.value.trim();

            if (q.length < 2) {
                suggestionsBox.classList.remove('active');
                suggestionsBox.innerHTML = '';
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch(`/api/search-suggestions/?q=${encodeURIComponent(q)}`)
                    .then(r => r.json())
                    .then(data => {
                        if (!data.results || !data.results.length) {
                            suggestionsBox.classList.remove('active');
                            suggestionsBox.innerHTML = '';
                            return;
                        }
                        activeIndex = -1;
                        suggestionsBox.innerHTML = data.results.map((job, i) => `
                            <div class="search-suggestion-item" data-index="${i}" data-url="/jobs/${job.pk}/">
                                <div>
                                    <div class="suggestion-title">${escapeHtml(job.title)}</div>
                                    <div class="suggestion-meta">${escapeHtml(job.company__company_name || '')} ${job.location ? '&middot; ' + escapeHtml(job.location) : ''}</div>
                                </div>
                            </div>
                        `).join('');
                        suggestionsBox.classList.add('active');

                        suggestionsBox.querySelectorAll('.search-suggestion-item').forEach(item => {
                            item.addEventListener('click', () => {
                                window.location.href = item.dataset.url;
                            });
                        });
                    })
                    .catch(() => {
                        suggestionsBox.classList.remove('active');
                    });
            }, 300);
        });

        // Keyboard navigation
        searchInput.addEventListener('keydown', (e) => {
            const items = suggestionsBox.querySelectorAll('.search-suggestion-item');
            if (!items.length) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = Math.min(activeIndex + 1, items.length - 1);
                updateActiveItem(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, -1);
                updateActiveItem(items);
            } else if (e.key === 'Enter' && activeIndex >= 0) {
                e.preventDefault();
                window.location.href = items[activeIndex].dataset.url;
            } else if (e.key === 'Escape') {
                suggestionsBox.classList.remove('active');
            }
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                suggestionsBox.classList.remove('active');
            }
        });
    }

    function updateActiveItem(items) {
        items.forEach((item, i) => {
            item.classList.toggle('active', i === activeIndex);
        });
    }


    // ── Client-side Form Validation ────────────────
    document.querySelectorAll('form[novalidate]').forEach(form => {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');

        inputs.forEach(input => {
            input.addEventListener('blur', () => validateField(input));
            input.addEventListener('input', () => {
                if (input.classList.contains('is-invalid')) {
                    validateField(input);
                }
            });
        });

        // Password match validation
        const pw1 = form.querySelector('input[name="password1"], input[name="password"]');
        const pw2 = form.querySelector('input[name="password2"], input[name="password_confirm"]');
        if (pw1 && pw2) {
            pw2.addEventListener('blur', () => {
                if (pw2.value && pw1.value !== pw2.value) {
                    setFieldError(pw2, 'Passwords do not match');
                } else if (pw2.value) {
                    clearFieldError(pw2);
                }
            });

            // Password strength meter
            const strengthDiv = document.createElement('div');
            strengthDiv.className = 'password-strength';
            strengthDiv.innerHTML = '<div class="strength-bar"></div>';
            pw1.parentNode.insertBefore(strengthDiv, pw1.nextSibling);

            pw1.addEventListener('input', () => {
                const bar = strengthDiv.querySelector('.strength-bar');
                const strength = getPasswordStrength(pw1.value);
                bar.style.width = strength.percent + '%';
                bar.style.background = strength.color;
            });
        }

        form.addEventListener('submit', (e) => {
            let valid = true;
            inputs.forEach(input => {
                if (!validateField(input)) valid = false;
            });
            if (pw1 && pw2 && pw2.value && pw1.value !== pw2.value) {
                setFieldError(pw2, 'Passwords do not match');
                valid = false;
            }
            if (!valid) e.preventDefault();
        });
    });

    function validateField(input) {
        const value = input.value.trim();

        if (input.required && !value) {
            setFieldError(input, 'This field is required');
            return false;
        }

        if (input.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
            setFieldError(input, 'Please enter a valid email');
            return false;
        }

        if (input.name === 'phone' && value && !/^[\d\s+\-()]{7,15}$/.test(value)) {
            setFieldError(input, 'Please enter a valid phone number');
            return false;
        }

        clearFieldError(input);
        return true;
    }

    function setFieldError(input, message) {
        input.classList.add('is-invalid');
        input.classList.remove('is-valid');
        let errorDiv = input.parentNode.querySelector('.field-error');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.className = 'field-error';
            input.parentNode.appendChild(errorDiv);
        }
        errorDiv.textContent = message;
    }

    function clearFieldError(input) {
        input.classList.remove('is-invalid');
        if (input.value.trim()) input.classList.add('is-valid');
        const errorDiv = input.parentNode.querySelector('.field-error');
        if (errorDiv) errorDiv.remove();
    }

    function getPasswordStrength(pw) {
        let score = 0;
        if (pw.length >= 8) score++;
        if (pw.length >= 12) score++;
        if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++;
        if (/\d/.test(pw)) score++;
        if (/[^a-zA-Z0-9]/.test(pw)) score++;

        const levels = [
            { percent: 20, color: 'var(--danger)' },
            { percent: 40, color: 'var(--danger)' },
            { percent: 60, color: 'var(--warning)' },
            { percent: 80, color: 'var(--info)' },
            { percent: 100, color: 'var(--success)' }
        ];
        return levels[Math.min(score, levels.length - 1)];
    }


    // ── Newsletter AJAX Submit ─────────────────────
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const emailInput = newsletterForm.querySelector('input[type="email"]');
            const email = emailInput.value.trim();
            if (!email) return;

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || getCookie('csrftoken');

            fetch('/newsletter/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': csrfToken
                },
                body: `email=${encodeURIComponent(email)}`
            })
            .then(r => r.json())
            .then(data => {
                showToast(data.success ? 'success' : 'warning', data.message);
                if (data.success) emailInput.value = '';
            })
            .catch(() => {
                showToast('danger', 'Something went wrong. Please try again.');
            });
        });
    }


    // ── Utility Functions ──────────────────────────
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCookie(name) {
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            c = c.trim();
            if (c.startsWith(name + '=')) {
                return decodeURIComponent(c.substring(name.length + 1));
            }
        }
        return '';
    }

});
