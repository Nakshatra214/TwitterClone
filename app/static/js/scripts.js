// Handle tweet form submission
document.addEventListener('DOMContentLoaded', function() {
    // Tweet Form Submission
    const tweetForm = document.querySelector('.tweet-form form');
    if (tweetForm) {
        tweetForm.addEventListener('submit', function(e) {
            const tweetContent = this.querySelector('textarea[name="content"]').value.trim();
            if (!tweetContent) {
                e.preventDefault();
                alert('Please enter a tweet before submitting.');
            }
        });
    }

    // Image Preview for Tweet Form
    const tweetImageInput = document.querySelector('input[name="image_file"]');
    if (tweetImageInput) {
        tweetImageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const preview = document.querySelector('.tweet-form .image-preview');
                    if (preview) {
                        preview.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded mb-2" style="max-height: 200px;">`;
                    }
                }
                reader.readAsDataURL(file);
            }
        });
    }

    // Tweet Actions (Like, Retweet)
    document.querySelectorAll('.tweet-actions a').forEach(action => {
        action.addEventListener('click', function(e) {
            e.preventDefault();
            const actionType = this.dataset.action;
            const tweetId = this.dataset.tweetId;
            
            fetch(this.href, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update the UI
                    const countElement = this.querySelector('span');
                    const iconElement = this.querySelector('i');
                    
                    if (actionType === 'like') {
                        countElement.textContent = data.likes_count;
                        iconElement.classList.toggle('text-danger');
                    } else if (actionType === 'retweet') {
                        countElement.textContent = data.retweets_count;
                        iconElement.classList.toggle('text-success');
                    }
                }
            })
            .catch(error => console.error('Error:', error));
        });
    });

    // Mobile Menu Toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });

        // Close mobile menu when clicking outside
        document.addEventListener('click', function(e) {
            if (!navbarCollapse.contains(e.target) && !navbarToggler.contains(e.target)) {
                navbarCollapse.classList.remove('show');
            }
        });
    }

    // Auto-resize textarea
    const tweetTextarea = document.querySelector('.tweet-form textarea');
    if (tweetTextarea) {
        tweetTextarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }

    // Character counter for tweet
    const tweetContent = document.querySelector('.tweet-form textarea[name="content"]');
    const charCounter = document.querySelector('.char-counter');
    const maxLength = 280;

    if (tweetContent && charCounter) {
        tweetContent.addEventListener('input', function() {
            const remaining = maxLength - this.value.length;
            charCounter.textContent = remaining;
            
            if (remaining < 0) {
                charCounter.classList.add('text-danger');
            } else {
                charCounter.classList.remove('text-danger');
            }
        });
    }

    // Flash message auto-dismiss
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.classList.add('fade');
            setTimeout(() => {
                message.remove();
            }, 300);
        }, 5000);
    });

    // Infinite scroll for tweets
    let isLoading = false;
    let page = 1;
    const tweetsContainer = document.querySelector('.tweets-feed');
    const loadMoreTrigger = document.querySelector('.load-more-trigger');

    if (tweetsContainer && loadMoreTrigger) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting && !isLoading) {
                    loadMoreTweets();
                }
            });
        });

        observer.observe(loadMoreTrigger);

        function loadMoreTweets() {
            isLoading = true;
            page++;

            fetch(`/api/tweets?page=${page}`)
                .then(response => response.json())
                .then(data => {
                    if (data.tweets.length > 0) {
                        data.tweets.forEach(tweet => {
                            const tweetElement = createTweetElement(tweet);
                            tweetsContainer.appendChild(tweetElement);
                        });
                    } else {
                        loadMoreTrigger.style.display = 'none';
                    }
                    isLoading = false;
                })
                .catch(error => {
                    console.error('Error loading more tweets:', error);
                    isLoading = false;
                });
        }

        function createTweetElement(tweet) {
            const div = document.createElement('div');
            div.className = 'card mb-3 tweet-card';
            div.innerHTML = `
                <div class="card-body">
                    <div class="d-flex">
                        <img src="/static/profile_pics/${tweet.author.profile_image}" class="rounded-circle me-3" width="50" height="50">
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between">
                                <h5 class="card-title mb-0">
                                    <a href="/profile/${tweet.author.username}" class="text-decoration-none">${tweet.author.username}</a>
                                </h5>
                                <small class="text-muted">${new Date(tweet.created_at).toLocaleDateString()}</small>
                            </div>
                            <p class="card-text mt-2">${tweet.content}</p>
                            ${tweet.image ? `<img src="/static/tweets/${tweet.image}" class="img-fluid rounded mb-2 tweet-image">` : ''}
                            <div class="d-flex justify-content-between mt-3">
                                <div class="tweet-actions">
                                    <a href="/like/${tweet.id}" class="text-decoration-none text-muted me-3" data-action="like" data-tweet-id="${tweet.id}">
                                        <i class="fas fa-heart ${tweet.has_liked ? 'text-danger' : ''}"></i>
                                        <span>${tweet.likes_count}</span>
                                    </a>
                                    <a href="/retweet/${tweet.id}" class="text-decoration-none text-muted" data-action="retweet" data-tweet-id="${tweet.id}">
                                        <i class="fas fa-retweet ${tweet.has_retweeted ? 'text-success' : ''}"></i>
                                        <span>${tweet.retweets_count}</span>
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            return div;
        }
    }

    // Tweet template
    const tweetTemplate = (tweet) => `
        <div class="card tweet-card mb-3 animate-in">
            <div class="card-body">
                <div class="d-flex">
                    <img src="${tweet.author_image}" class="rounded-circle me-3" width="50" height="50" alt="Profile Picture">
                    <div class="flex-grow-1">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-0">${tweet.author_name}</h6>
                                <small class="text-muted">@${tweet.author_username} · ${formatDate(tweet.created_at)}</small>
                            </div>
                            ${tweet.is_author ? `
                            <div class="dropdown">
                                <button class="btn btn-link text-muted" type="button" data-bs-toggle="dropdown">
                                    <i class="fas fa-ellipsis-h"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><button class="dropdown-item text-danger delete-tweet" data-tweet-id="${tweet.id}">Delete</button></li>
                                </ul>
                            </div>
                            ` : ''}
                        </div>
                        <p class="card-text mt-2">${tweet.content}</p>
                        ${tweet.image ? `<img src="/static/tweets/${tweet.image}" class="img-fluid rounded mb-2 tweet-image">` : ''}
                        <div class="tweet-actions mt-3">
                            <button class="btn btn-link text-muted p-0 me-3" data-action="like" data-tweet-id="${tweet.id}">
                                <i class="far fa-heart${tweet.liked ? ' text-danger fas' : ''}"></i>
                                <span class="likes-count">${tweet.likes_count}</span>
                            </button>
                            <button class="btn btn-link text-muted p-0 me-3" data-action="retweet" data-tweet-id="${tweet.id}">
                                <i class="fas fa-retweet${tweet.retweeted ? ' text-success' : ''}"></i>
                                <span class="retweets-count">${tweet.retweets_count}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}); 