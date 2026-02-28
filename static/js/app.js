document.addEventListener('DOMContentLoaded', () => {

    // ━━━ GSAP Animations ━━━
    gsap.registerPlugin(ScrollTrigger);

    // Animate elements with .fade-up class
    gsap.utils.toArray('.fade-up').forEach(element => {
        gsap.fromTo(element,
            {
                y: 30,
                opacity: 0
            },
            {
                y: 0,
                opacity: 1,
                duration: 1,
                ease: "power3.out",
                scrollTrigger: {
                    trigger: element,
                    start: "top 85%", // Animation starts when top of element hits 85% of viewport height
                    toggleActions: "play none none reverse"
                }
            }
        );
    });

    // Magnetic Buttons
    const magneticBtns = document.querySelectorAll(".btn-magnetic");
    magneticBtns.forEach((btn) => {
        btn.addEventListener("mousemove", (e) => {
            const position = btn.getBoundingClientRect();
            const x = e.pageX - position.left - position.width / 2;
            const y = e.pageY - position.top - position.height / 2;

            btn.style.transform = `translate(${x * 0.3}px, ${y * 0.3}px)`;
        });

        btn.addEventListener("mouseout", () => {
            btn.style.transform = "translate(0px, 0px)";
        });
    });
    // ━━━ 3. Stagger Card Animations ━━━
    document.querySelectorAll('.row').forEach(row => {
        const cards = row.querySelectorAll('.glass-card, .company-card, .stat-card');
        if (cards.length > 1) {
            gsap.fromTo(cards,
                { y: 40, opacity: 0 },
                {
                    y: 0,
                    opacity: 1,
                    duration: 0.8,
                    stagger: 0.1,
                    ease: "power3.out",
                    scrollTrigger: {
                        trigger: row,
                        start: "top 85%",
                        toggleActions: "play none none reverse"
                    }
                }
            );
        }
    });

    // ━━━ 4. Counter Animation ━━━
    document.querySelectorAll('[data-count]').forEach(el => {
        const target = parseInt(el.dataset.count) || 0;
        const counter = { val: 0 };
        gsap.to(counter, {
            val: target,
            duration: 2,
            ease: "power2.out",
            scrollTrigger: {
                trigger: el,
                start: "top 90%",
                toggleActions: "play none none none"
            },
            onUpdate: () => {
                el.textContent = Math.round(counter.val) + '+';
            }
        });
    });

    // Spotlight Effect (throttled for performance)
    {
        const glassCards = document.querySelectorAll('.glass-card');
        let ticking = false;
        document.addEventListener('mousemove', (e) => {
            if (ticking) return;
            ticking = true;
            requestAnimationFrame(() => {
                glassCards.forEach(card => {
                    const rect = card.getBoundingClientRect();
                    // Only update cards near the cursor (within 400px)
                    if (e.clientX < rect.left - 400 || e.clientX > rect.right + 400 ||
                        e.clientY < rect.top - 400 || e.clientY > rect.bottom + 400) return;
                    const x = e.clientX - rect.left;
                    const y = e.clientY - rect.top;
                    card.style.background = `
                    radial-gradient(600px circle at ${x}px ${y}px, rgba(79, 70, 229, 0.06), transparent 40%),
                    var(--bg-card)
                `;
                });
                ticking = false;
            });
        }, { passive: true });
    }

}); // End DOMContentLoaded
