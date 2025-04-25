// Get elements and data
const progressBar = document.getElementById('generationProgress');
const statusMessage = document.getElementById('statusMessage');
const portfolioId = progressBar.dataset.portfolioId;
const viewPortfolioUrl = progressBar.dataset.viewUrl;
const statusUrl = progressBar.dataset.statusUrl;
const templatesUrl = progressBar.dataset.templatesUrl;

console.log('Initial data:', {
    portfolioId,
    viewPortfolioUrl,
    statusUrl,
    templatesUrl
});

let progress = 0;
let isComplete = false;
let checkCount = 0;
const MAX_CHECKS = 60; // Maximum number of status checks (2 minutes)

const statusMessages = [
    "Parsing your resume",
    "Analyzing your experience",
    "Generating content",
    "Creating portfolio structure",
    "Finalizing your portfolio"
];

function updateProgress() {
    if (progress < 90) {  // Only update progress up to 90%
        progress += 10;
        progressBar.style.width = `${progress}%`;
        progressBar.textContent = `${progress}%`;
        
        // Update status message based on progress
        const messageIndex = Math.min(Math.floor(progress / 20), statusMessages.length - 1);
        statusMessage.textContent = statusMessages[messageIndex];
        
        setTimeout(updateProgress, 2000);
    }
}

// Check if portfolio is generated
function checkPortfolioGenerated() {
    if (checkCount >= MAX_CHECKS) {
        statusMessage.textContent = 'Generation is taking longer than expected. Please try again.';
        progressBar.classList.remove('progress-bar-striped', 'progress-bar-animated');
        progressBar.classList.add('bg-warning');
        return;
    }

    checkCount++;
    console.log(`Checking portfolio status (attempt ${checkCount}) at URL:`, statusUrl);
    
    // Check if the portfolio file exists
    fetch(statusUrl)
        .then(response => {
            console.log('Response status:', response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Portfolio check response:', data);
            
            if (data.status === 'complete') {
                console.log('Portfolio generation complete, redirecting to:', viewPortfolioUrl);
                isComplete = true;
                // Update progress to 100% when complete
                progress = 100;
                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                statusMessage.textContent = 'Portfolio generated successfully!';
                
                // Redirect to view the portfolio
                setTimeout(() => {
                    window.location.href = viewPortfolioUrl;
                }, 1000);
            } else {
                console.log('Portfolio still processing, status:', data.status);
                // Still processing
                setTimeout(checkPortfolioGenerated, 2000);
            }
        })
        .catch(error => {
            console.error('Error checking portfolio:', error);
            statusMessage.textContent = 'Error checking portfolio. Retrying...';
            setTimeout(checkPortfolioGenerated, 2000);
        });
}

// Initialize loading functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('Loading page initialized');
    // Start the progress animation
    updateProgress();
    // Start checking portfolio generation
    checkPortfolioGenerated();
}); 