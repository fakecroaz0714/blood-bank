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

// ---------------------------------------------------------
// Meta WhatsApp Cloud API & Emergency Broadcast Controller
// ---------------------------------------------------------

document.addEventListener('DOMContentLoaded', function() {
    const waModal = document.getElementById('whatsappBroadcastModal');
    if (!waModal) return;

    const bloodGroupSelect = document.getElementById('waTargetBloodGroup');
    const cityInput = document.getElementById('waTargetCity');
    const verifiedCheck = document.getElementById('waVerifiedOnly');
    const availableCheck = document.getElementById('waAvailableOnly');

    const patientInput = document.getElementById('waPatientName');
    const unitsInput = document.getElementById('waUnitsNeeded');
    const urgencySelect = document.getElementById('waUrgency');
    const hospitalInput = document.getElementById('waHospital');
    const phoneInput = document.getElementById('waContactPhone');
    const notesInput = document.getElementById('waNotes');

    const previewContainer = document.getElementById('waPreviewText');
    const matchingCountBadge = document.getElementById('waMatchingCount');
    const donorPillContainer = document.getElementById('waDonorPillContainer');

    const form = document.getElementById('whatsappBroadcastForm');
    const submitBtn = document.getElementById('btnSubmitWhatsappBroadcast');
    const btnSpinner = document.getElementById('btnWaSpinner');
    const btnText = document.getElementById('btnWaSubmitText');

    const statusBanner = document.getElementById('whatsappStatusText');
    const statusBadge = document.getElementById('whatsappStatusBadge');
    const resultsContainer = document.getElementById('waResultsContainer');
    const summaryReport = document.getElementById('waSummaryReport');
    const recipientList = document.getElementById('waRecipientList');

    function updatePreviewBubble() {
        if (!previewContainer) return;
        const patient = (patientInput && patientInput.value.trim()) || '[Patient Name]';
        const bg = (bloodGroupSelect && bloodGroupSelect.value !== 'All') ? bloodGroupSelect.value : 'URGENT';
        const units = (unitsInput && unitsInput.value.trim()) || '1';
        const urgency = (urgencySelect && urgencySelect.value) || 'Urgent';
        const hospital = (hospitalInput && hospitalInput.value.trim()) || '[Hospital Name]';
        const city = (cityInput && cityInput.value.trim()) || '[City]';
        const phone = (phoneInput && phoneInput.value.trim()) || '[Coordinator Phone]';
        const notes = (notesInput && notesInput.value.trim()) || '';

        let preview = `🚨 <strong>CRITICAL BLOOD ALERT - BloodConnect</strong> 🚨\n\n`;
        preview += `Dear Volunteer Donor,\n`;
        preview += `An emergency blood request matching your blood group (<strong>${escapeHtml(bg)}</strong>) has just been posted in <strong>${escapeHtml(city)}</strong>.\n\n`;
        preview += `📋 <strong>Request Summary:</strong>\n`;
        preview += `• Blood Group: <strong>${escapeHtml(bg)}</strong> (${escapeHtml(units)} Unit(s))\n`;
        preview += `• Patient: <strong>${escapeHtml(patient)}</strong>\n`;
        preview += `• Urgency: ⚡ <strong>${escapeHtml(urgency.toUpperCase())}</strong>\n`;
        preview += `• Hospital: <strong>${escapeHtml(hospital)}</strong>\n`;
        preview += `• Contact Phone: <strong>${escapeHtml(phone)}</strong>\n`;
        if (notes) {
            preview += `• Notes: ${escapeHtml(notes)}\n`;
        }
        preview += `\n🙏 If you are available to donate, please contact immediately at <strong>${escapeHtml(phone)}</strong>!`;

        previewContainer.innerHTML = preview;
    }

    function checkApiStatus() {
        fetch('/api/whatsapp/status')
            .then(res => res.json())
            .then(data => {
                if (data.is_configured) {
                    if (statusBanner) statusBanner.innerHTML = '<strong>Meta WhatsApp Cloud API Connected:</strong> Alerts are transmitted directly to recipient phones via official Meta Graph API.';
                    if (statusBadge) {
                        statusBadge.className = 'badge bg-success';
                        statusBadge.innerHTML = '<i class="bi bi-broadcast"></i> Live Meta Cloud API';
                    }
                } else {
                    if (statusBanner) statusBanner.innerHTML = '<strong>Interactive Simulation & Direct Chat Mode:</strong> Configure <code>WHATSAPP_ACCESS_TOKEN</code> in <code>.env</code> for official Meta Cloud API transmission. 1-Click WhatsApp direct chat links are active.';
                    if (statusBadge) {
                        statusBadge.className = 'badge bg-primary';
                        statusBadge.innerHTML = '<i class="bi bi-lightning-charge"></i> Live Simulation Mode';
                    }
                }
            })
            .catch(() => {
                if (statusBanner) statusBanner.textContent = 'WhatsApp service ready.';
            });
    }

    let searchTimeout = null;
    function fetchMatchingDonors() {
        const bg = (bloodGroupSelect && bloodGroupSelect.value) || 'All';
        const city = (cityInput && cityInput.value.trim()) || '';
        const verified = (verifiedCheck && verifiedCheck.checked) ? '1' : '0';
        const available = (availableCheck && availableCheck.checked) ? '1' : '0';

        const params = new URLSearchParams({
            blood_group: bg,
            city: city,
            verified_only: verified,
            available_only: available
        });

        if (donorPillContainer) {
            donorPillContainer.innerHTML = '<span class="text-muted"><span class="spinner-border spinner-border-sm me-1"></span>Scanning registered donors...</span>';
        }

        fetch(`/api/whatsapp/matching-donors?${params.toString()}`)
            .then(res => res.json())
            .then(data => {
                const count = data.count || 0;
                if (matchingCountBadge) {
                    matchingCountBadge.textContent = count;
                    matchingCountBadge.className = count > 0 ? 'fs-6 text-success' : 'fs-6 text-secondary';
                }

                if (donorPillContainer) {
                    if (count === 0) {
                        donorPillContainer.innerHTML = `
                            <div class="text-danger small">
                                <i class="bi bi-exclamation-circle me-1"></i> No matching registered donors found currently in the database. 
                                <span class="text-muted">(Broadcast will be ready as soon as matching donors register).</span>
                            </div>`;
                    } else {
                        const pills = data.donors.slice(0, 5).map(d => 
                            `<span class="badge bg-light text-dark border me-1 mb-1">
                                <i class="bi bi-person-fill text-danger me-1"></i>${escapeHtml(d.name)} (${d.blood_group} - ${escapeHtml(d.city)})
                            </span>`
                        ).join('');
                        const extra = count > 5 ? `<span class="badge bg-secondary">+${count - 5} more</span>` : '';
                        donorPillContainer.innerHTML = `<div class="d-flex flex-wrap align-items-center"><span class="me-2 small fw-bold text-muted">Recipients:</span>${pills}${extra}</div>`;
                    }
                }
            })
            .catch(err => {
                console.error("Donor query failed:", err);
                if (donorPillContainer) donorPillContainer.innerHTML = '<span class="text-muted small">Could not load live donor count.</span>';
            });
    }

    // Modal shown event
    waModal.addEventListener('shown.bs.modal', function() {
        checkApiStatus();
        fetchMatchingDonors();
        updatePreviewBubble();
    });

    // Inputs listeners for real-time preview and donor targeting
    [bloodGroupSelect, verifiedCheck, availableCheck].forEach(el => {
        if (el) el.addEventListener('change', () => {
            fetchMatchingDonors();
            updatePreviewBubble();
        });
    });

    if (cityInput) {
        cityInput.addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                fetchMatchingDonors();
                updatePreviewBubble();
            }, 300);
        });
    }

    [patientInput, unitsInput, urgencySelect, hospitalInput, phoneInput, notesInput].forEach(el => {
        if (el) el.addEventListener('input', updatePreviewBubble);
    });

    // Handle Broadcast Submit
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            if (!patientInput.value.trim() || !hospitalInput.value.trim() || !phoneInput.value.trim()) {
                showToast('Missing Fields', 'Please provide patient name, hospital, and emergency contact phone.', 'danger');
                return;
            }

            // Set loading state
            submitBtn.disabled = true;
            btnSpinner.classList.remove('d-none');
            btnText.textContent = 'Transmitting WhatsApp Messages...';

            const payload = {
                patient_name: patientInput.value.trim(),
                hospital: hospitalInput.value.trim(),
                contact_phone: phoneInput.value.trim(),
                blood_group: bloodGroupSelect.value,
                city: cityInput.value.trim(),
                urgency: urgencySelect.value,
                units_needed: unitsInput.value,
                notes: notesInput.value.trim(),
                verified_only: verifiedCheck.checked ? 1 : 0,
                available_only: availableCheck.checked ? 1 : 0
            };

            fetch('/api/whatsapp/broadcast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                submitBtn.disabled = false;
                btnSpinner.classList.add('d-none');
                btnText.textContent = 'Send WhatsApp Emergency Broadcast';

                if (resultsContainer) resultsContainer.classList.remove('d-none');

                if (data.total_targeted === 0) {
                    summaryReport.innerHTML = `
                        <div class="text-warning">
                            <i class="bi bi-info-circle me-1"></i> ${escapeHtml(data.error || 'No matching registered donors found.')}
                        </div>`;
                    if (recipientList) recipientList.innerHTML = '<div class="list-group-item text-muted small">No donors targeted.</div>';
                    showToast('No Recipients', 'No registered donors matched the selected blood group and city criteria.', 'warning');
                    return;
                }

                if (data.success) {
                    const modeLabel = data.is_live_meta ? 
                        '<span class="badge bg-success"><i class="bi bi-broadcast"></i> Official Meta Cloud API (Sent)</span>' : 
                        '<span class="badge bg-primary"><i class="bi bi-check2-circle"></i> Simulation & 1-Click Link Mode</span>';

                    summaryReport.innerHTML = `
                        <div class="mb-2">${modeLabel}</div>
                        <div>Successfully broadcasted emergency alert to <strong>${data.sent_count}</strong> of <strong>${data.total_targeted}</strong> registered volunteer donor(s).</div>
                    `;

                    if (recipientList && data.results) {
                        recipientList.innerHTML = data.results.map(r => {
                            const badge = r.success ? 
                                '<span class="badge bg-success-subtle text-success border border-success-subtle">Dispatched</span>' : 
                                '<span class="badge bg-danger-subtle text-danger border border-danger-subtle">Error</span>';
                            
                            return `
                                <div class="list-group-item d-flex justify-content-between align-items-center py-2 px-3">
                                    <div>
                                        <div class="fw-bold text-dark small">${escapeHtml(r.donor_name || 'Donor')}</div>
                                        <div class="font-monospace text-muted" style="font-size: 0.78rem;">
                                            <i class="bi bi-telephone-outbound me-1"></i>+${escapeHtml(r.phone)}
                                        </div>
                                    </div>
                                    <div class="d-flex align-items-center gap-2">
                                        ${badge}
                                        <a href="${r.wa_link}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-outline-success" title="Open direct WhatsApp conversation">
                                            <i class="bi bi-whatsapp me-1"></i> Open Chat
                                        </a>
                                    </div>
                                </div>
                            `;
                        }).join('');
                    }

                    showToast('WhatsApp Dispatched', `Emergency message transmitted to ${data.sent_count} registered donor(s).`, 'success');
                    resultsContainer.scrollIntoView({ behavior: 'smooth' });
                } else {
                    summaryReport.innerHTML = `<div class="text-danger"><i class="bi bi-x-circle me-1"></i> ${escapeHtml(data.error || 'Failed to dispatch broadcast.')}</div>`;
                    showToast('Broadcast Failed', data.error || 'Failed to dispatch alert.', 'danger');
                }
            })
            .catch(err => {
                console.error("Broadcast request failed:", err);
                submitBtn.disabled = false;
                btnSpinner.classList.add('d-none');
                btnText.textContent = 'Send WhatsApp Emergency Broadcast';
                showToast('Network Error', 'Failed to connect to WhatsApp dispatch service.', 'danger');
            });
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.toString().replace(/[&<>"']/g, function(m) { return map[m]; });
    }
});
