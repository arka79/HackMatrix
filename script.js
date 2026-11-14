// ==========================================================================
// CI Doctor - Frontend Interactivity
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // ---------------------------------------------------------------
    // Tab switching for command reference
    // ---------------------------------------------------------------
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            const tabId = btn.getAttribute('data-tab');
            const activeContent = document.getElementById(`tab-${tabId}`);
            if (activeContent) {
                activeContent.classList.add('active');
            }
        });
    });

    // ---------------------------------------------------------------
    // Theme toggle (light / dark)
    // ---------------------------------------------------------------
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;

    const savedTheme = localStorage.getItem('ci-doctor-theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');

    setTheme(initialTheme);

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const current = html.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            setTheme(next);
        });
    }

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('ci-doctor-theme', theme);
        if (themeToggle) {
            themeToggle.textContent = theme === 'dark' ? 'Light' : 'Dark';
        }
    }

    // ---------------------------------------------------------------
    // Copy to clipboard (event delegation - works for all buttons)
    // ---------------------------------------------------------------
    document.body.addEventListener('click', (event) => {
        const btn = event.target.closest('[data-copy]');
        if (!btn) return;

        event.preventDefault();
        const command = btn.getAttribute('data-copy');

        navigator.clipboard.writeText(command).then(() => {
            const originalText = btn.textContent;
            btn.textContent = 'Copied';
            btn.style.background = 'var(--color-accent)';
            btn.style.color = 'var(--color-accent-foreground)';
            btn.style.borderColor = 'var(--color-accent)';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
                btn.style.color = '';
                btn.style.borderColor = '';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy:', err);
        });
    });

    // ---------------------------------------------------------------
    // FAQ accordion
    // ---------------------------------------------------------------
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const answer = question.nextElementSibling;
            const isOpen = answer.style.maxHeight && answer.style.maxHeight !== '0px';

            document.querySelectorAll('.faq-answer').forEach(a => {
                a.style.maxHeight = '0';
            });

            if (!isOpen) {
                answer.style.maxHeight = answer.scrollHeight + 'px';
            }
        });
    });

    // ---------------------------------------------------------------
    // Smooth scroll helper
    // ---------------------------------------------------------------
    window.scrollToSection = (sectionId) => {
        document.querySelector(sectionId).scrollIntoView({ behavior: 'smooth' });
    };

    // ---------------------------------------------------------------
    // Add copy buttons to code blocks in steps
    // ---------------------------------------------------------------
    document.querySelectorAll('.step-content .code-block pre').forEach((pre) => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-sm btn-ghost';
        btn.textContent = 'Copy';
        btn.setAttribute('data-copy', pre.textContent);
        btn.onclick = (e) => {
            e.stopPropagation();
            const code = pre.textContent;
            navigator.clipboard.writeText(code).then(() => {
                btn.textContent = 'Copied';
                btn.style.background = 'var(--color-accent)';
                btn.style.color = 'var(--color-accent-foreground)';
                btn.style.borderColor = 'var(--color-accent)';
                setTimeout(() => {
                    btn.textContent = 'Copy';
                    btn.style.background = '';
                    btn.style.color = '';
                    btn.style.borderColor = '';
                }, 2000);
            });
        };
        pre.parentElement.appendChild(btn);
    });

    // ---------------------------------------------------------------
    // Highlight current section in nav on scroll
    // ---------------------------------------------------------------
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.nav-link');

    window.addEventListener('scroll', () => {
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            if (window.pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });

    // ---------------------------------------------------------------
    // Interactive Grid (converted from React component)
    // A grid whose cells light up under the pointer and fade out behind it.
    // ---------------------------------------------------------------
    const cellSize = 40;
    const svg = document.querySelector('.interactive-grid');
    const hero = document.querySelector('.hero');

    if (svg && hero) {
        let size = { columns: 0, rows: 0 };
        let active = null;

        function resize() {
            const { width, height } = svg.getBoundingClientRect();
            size = {
                columns: Math.ceil(width / cellSize),
                rows: Math.ceil(height / cellSize),
            };
            render();
        }

        function render() {
            svg.innerHTML = '';
            const total = size.columns * size.rows;
            for (let i = 0; i < total; i++) {
                const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                rect.setAttribute('x', (i % size.columns) * cellSize);
                rect.setAttribute('y', Math.floor(i / size.columns) * cellSize);
                rect.setAttribute('width', cellSize);
                rect.setAttribute('height', cellSize);
                rect.setAttribute('fill', 'currentColor');
                rect.setAttribute('stroke', 'currentColor');
                rect.setAttribute('stroke-opacity', '0.1');
                rect.className = 'grid-cell';
                if (i === active) {
                    rect.style.fillOpacity = '0.15';
                    rect.style.transition = 'fill-opacity 0s';
                } else {
                    rect.style.fillOpacity = '0';
                    rect.style.transition = 'fill-opacity 1s ease-out';
                }
                svg.appendChild(rect);
            }
        }

        function onPointerMove(event) {
            const bounds = svg.getBoundingClientRect();
            const column = Math.floor((event.clientX - bounds.left) / cellSize);
            const row = Math.floor((event.clientY - bounds.top) / cellSize);
            const columns = Math.ceil(bounds.width / cellSize);
            const newActive =
                column >= 0 && row >= 0 && column < columns
                    ? row * columns + column
                    : null;
            if (newActive !== active) {
                active = newActive;
                render();
            }
        }

        function onPointerLeave() {
            active = null;
            render();
        }

        const resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(svg);

        hero.addEventListener('pointermove', onPointerMove);
        hero.addEventListener('pointerleave', onPointerLeave);

        resize();
    }
});
