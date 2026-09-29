// BloodConnect Main JavaScript Helpers

document.addEventListener('DOMContentLoaded', function() {
    // 1. Auto-dismiss Bootstrap alerts after 5 seconds
    setTimeout(function() {
        if (typeof bootstrap !== 'undefined' && bootstrap.Alert) {
            const alerts = document.querySelectorAll('.alert-dismissible');
            alerts.forEach(function(alert) {
                if (alert && alert.isConnected) {
                    try {
                        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                        if (bsAlert) bsAlert.close();
                    } catch (e) {
                        console.debug("Alert already dismissed:", e);
                    }
                }
            });
        }
    }, 5000);

    // 2. Donor Availability Toggle Handler
    const availabilityToggle = document.getElementById('availabilityToggle');
    if (availabilityToggle) {
        availabilityToggle.addEventListener('change', function(e) {
            const isChecked = this.checked;
            const statusLabel = document.getElementById('availabilityLabel');
            
            fetch('/api/donor/toggle-availability', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ is_available: isChecked ? 1 : 0 })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (statusLabel) {
                        statusLabel.textContent = isChecked ? 'Available for Donation' : 'Currently Unavailable';
                        statusLabel.className = isChecked ? 'fw-bold text-success' : 'fw-bold text-secondary';
                    }
                    showToast('Status Updated', `You are now marked as ${isChecked ? 'Available' : 'Unavailable'}.`, isChecked ? 'success' : 'secondary');
                } else {
                    this.checked = !isChecked; // revert
                    showToast('Error', data.error || 'Failed to update availability status', 'danger');
                }
            })
            .catch(err => {
                console.error(err);
                this.checked = !isChecked;
                showToast('Network Error', 'Could not update status. Please try again.', 'danger');
            });
        });
    }

    // 3. Dynamic Eligibility Calculator on Date input change
    const donationDateInput = document.getElementById('lastDonationDateInput');
    if (donationDateInput) {
        donationDateInput.addEventListener('change', function() {
            calculateEligibility(this.value);
        });
        // Initial run
        if (donationDateInput.value) {
            calculateEligibility(donationDateInput.value);
        }
    }

    // 4. Copy Phone to Clipboard Helper
    document.querySelectorAll('.btn-copy-phone').forEach(btn => {
        btn.addEventListener('click', function() {
            const phone = this.getAttribute('data-phone');
            if (navigator.clipboard && phone) {
                navigator.clipboard.writeText(phone).then(() => {
                    const origHtml = this.innerHTML;
                    this.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                    setTimeout(() => { this.innerHTML = origHtml; }, 2000);
                });
            }
        });
    });
});

/**
 * Calculates 90-day blood donation eligibility
 */
function calculateEligibility(dateString) {
    const badgeContainer = document.getElementById('eligibilityResult');
    if (!badgeContainer) return;

    if (!dateString) {
        badgeContainer.innerHTML = `
            <div class="alert alert-success d-flex align-items-center mb-0">
                <i class="bi bi-shield-check fs-4 me-2"></i>
                <div>
                    <strong>First-Time Donor / Eligible:</strong> You have not logged a previous donation. You are fully eligible to donate!
                </div>
            </div>`;
        return;
    }

    const lastDate = new Date(dateString);
    const today = new Date();
    const diffTime = today - lastDate;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    const waitingPeriodDays = 90; // Standard 3-month eligibility interval

    if (diffDays >= waitingPeriodDays) {
        badgeContainer.innerHTML = `
            <div class="alert alert-success d-flex align-items-center mb-0">
                <i class="bi bi-check-circle-fill fs-4 me-2"></i>
                <div>
                    <strong>Eligible to Donate:</strong> It has been ${diffDays} days since your last donation (90-day minimum satisfied).
                </div>
            </div>`;
    } else {
        const remainingDays = waitingPeriodDays - diffDays;
        const nextDate = new Date(lastDate);
        nextDate.setDate(nextDate.getDate() + waitingPeriodDays);
        const options = { year: 'numeric', month: 'short', day: 'numeric' };

        badgeContainer.innerHTML = `
            <div class="alert alert-warning d-flex align-items-center mb-0">
                <i class="bi bi-clock-history fs-4 me-2"></i>
                <div>
                    <strong>Recovery Period Active:</strong> Last donation was ${diffDays} days ago. Please wait <strong>${remainingDays} more day(s)</strong> (Eligible around ${nextDate.toLocaleDateString(undefined, options)}).
                </div>
            </div>`;
    }
}

/**
 * Lightweight Toast Notification helper
 */
function showToast(title, message, variant = 'info') {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }

    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${variant} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}:</strong> ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toastEl);
    if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const bsToast = new bootstrap.Toast(toastEl, { delay: 3500 });
        bsToast.show();
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    } else {
        setTimeout(() => toastEl.remove(), 3500);
    }
}
