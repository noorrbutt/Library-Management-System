const profileState = {
    isEditing: false,
    hasChanges: false,
    originalData: {},
    currentData: {},
    photoPreview: null,
    hasExistingPhoto: false
};

$(document).ready(function() {
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:/.test(settings.url) || /^https:/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", getCookie("csrftoken"));
            }
        }
    });

    initializeProfile();
    setupEventListeners();
    setupCollapsibleCards();
    displayAvatarInitials();
    checkForExistingPhoto();
    setupPhotoMenu();
});

function initializeProfile() {
    profileState.originalData = {
        fullName: $.trim($('#fullName').val()),
        email:    $.trim($('#emailAddress').val()),
        phone:    $.trim($('#phoneNumber').val()),
        dob:      $.trim($('#dateOfBirth').val()),
        address:  $.trim($('#address').val()),
        libraryName: $.trim($('#libraryName').val())
    };
    profileState.currentData = JSON.parse(JSON.stringify(profileState.originalData));
    setFieldsDisabled(true);
    updateButtonDisplay();
}

function setupEventListeners() {
    $('#editPersonalBtn').on('click', function(e) {
        e.preventDefault();
        profileState.isEditing ? savePersonalInfo() : enterEditMode();
    });

    $('#editLibraryBtn').on('click', function(e) {
        e.preventDefault();
        profileState.isEditing ? saveLibraryInfo() : enterLibraryEditMode();
    });

    $('#cancelPersonalBtn').on('click', function(e) {
        e.preventDefault();
        cancelEdit();
    });

    $('#cancelLibraryBtn').on('click', function(e) {
        e.preventDefault();
        cancelLibraryEdit();
    });

    $('#savePersonalBtn').on('click', function(e) {
        e.preventDefault();
        if (validatePersonalForm()) savePersonalInfo();
    });

    $('#saveLibraryBtn').on('click', function(e) {
        e.preventDefault();
        if (validateLibraryForm()) saveLibraryInfo();
    });

    $('#changePasswordBtn').on('click', function(e) {
        e.preventDefault();
        showPasswordChangeModal();
    });

    $('#photoInput').on('change', function(e) {
        handlePhotoUpload(e);
    });

    $('#fullName, #emailAddress, #phoneNumber, #dateOfBirth, #address, #libraryName').on('change input', function() {
        updateCurrentData();
        detectChanges();
        updateButtonState();
    });
}

function setupCollapsibleCards() {
    $('.collapsible-header').on('click', function() {
        $(this).parent('.collapsible-card').toggleClass('active');
    });
}

/* ─── Avatar initials ─────────────────────────────────────────────────── */

function displayAvatarInitials() {
    const el = document.getElementById('avatarInitials');
    if (el) {
        el.textContent = getInitials($.trim($('#fullName').val()));
    }
}

function getInitials(fullName) {
    if (!fullName) return 'U';
    const parts = fullName.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

/* ─── Photo state ─────────────────────────────────────────────────────── */

function checkForExistingPhoto() {
    const $img      = $('#avatarCircle').find('img.avatar-image');
    const $initials = $('#avatarInitials');

    if ($img.length > 0 && $img.attr('src')) {
        profileState.hasExistingPhoto = true;
        $('#avatarCircle').addClass('has-photo');
        $initials.hide();
        showPhotoMenu();
    } else {
        profileState.hasExistingPhoto = false;
        $('#avatarCircle').removeClass('has-photo');
        $initials.show();
        hidePhotoMenu();
    }
}

/* ─── Photo menu (change / remove) ───────────────────────────────────── */

function setupPhotoMenu() {
    /* Clicking the avatar circle when a photo exists opens the menu */
    $('#avatarCircle').on('click', function(e) {
        if (!profileState.hasExistingPhoto) return;
        e.stopPropagation();
        $('#photoMenu').toggleClass('photo-menu--open');
    });

    /* "Change photo" option */
    $(document).on('click', '#photoMenuChange', function(e) {
        e.stopPropagation();
        closePhotoMenu();
        $('#photoInput').val('').trigger('click');
    });

    /* "Remove photo" option */
    $(document).on('click', '#photoMenuRemove', function(e) {
        e.stopPropagation();
        closePhotoMenu();
        removePhoto();
    });

    /* Close menu when clicking elsewhere */
    $(document).on('click', function() {
        closePhotoMenu();
    });
}

function showPhotoMenu() {
    $('#photoMenuBtn').show();
}

function hidePhotoMenu() {
    $('#photoMenuBtn').hide();
    closePhotoMenu();
}

function closePhotoMenu() {
    $('#photoMenu').removeClass('photo-menu--open');
}

function removePhoto() {
    const confirmed = confirm('Remove your profile photo?');
    if (!confirmed) return;

    showLoading();

    $.ajax({
        url: '/remove-profile-photo/',
        type: 'POST',
        timeout: 30000,
        success: function() {
            hideLoading();
            $('#avatarCircle').find('img.avatar-image').remove();
            $('#avatarCircle').removeClass('has-photo');
            profileState.hasExistingPhoto = false;
            profileState.photoPreview     = null;
            $('#photoInput').val('');
            $('#avatarInitials').show();
            hidePhotoMenu();
            displayAvatarInitials();
            showSuccess('Profile photo removed.');
        },
        error: function(xhr) {
            hideLoading();
            let msg = 'Failed to remove photo. Please try again.';
            if (xhr.responseJSON && xhr.responseJSON.message) msg = xhr.responseJSON.message;
            showError(msg);
        }
    });
}

/* ─── Photo upload ────────────────────────────────────────────────────── */

function handlePhotoUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
        showError('Please select a valid image file.');
        return;
    }

    if (file.size > 5 * 1024 * 1024) {
        showError('Image size must be less than 5MB.');
        return;
    }

    const reader = new FileReader();

    reader.onload = function(event) {
        profileState.photoPreview = event.target.result;

        /* Show preview immediately */
        const $avatarCircle = $('#avatarCircle');
        const $initials     = $('#avatarInitials');
        let   $img          = $avatarCircle.find('img.avatar-image');

        if ($img.length > 0) {
            $img.attr('src', profileState.photoPreview);
        } else {
            $avatarCircle.prepend(
                $('<img>', {
                    src:   profileState.photoPreview,
                    alt:   'Profile Picture',
                    class: 'avatar-image',
                    css:   { width: '100%', height: '100%', objectFit: 'cover' }
                })
            );
        }

        $avatarCircle.addClass('has-photo');
        $initials.hide();

        /* Upload to server */
        showLoading();
        const formData = new FormData();
        formData.append('photo', file);
        formData.append('csrfmiddlewaretoken', getCookie('csrftoken'));

        $.ajax({
            url:         '/upload-profile-photo/',
            type:        'POST',
            data:        formData,
            processData: false,
            contentType: false,
            timeout:     30000,
            success: function(response) {
                hideLoading();
                profileState.hasExistingPhoto = true;
                showPhotoMenu();
                showSuccess('Profile photo updated successfully!');
            },
            error: function(xhr) {
                hideLoading();
                let msg = 'Failed to upload photo. Please try again.';
                if      (xhr.status === 404)                             msg = 'Upload endpoint not found.';
                else if (xhr.status === 403)                             msg = 'Permission denied. Please log in again.';
                else if (xhr.status === 400 && xhr.responseJSON?.message) msg = xhr.responseJSON.message;
                else if (xhr.responseJSON?.message)                       msg = xhr.responseJSON.message;

                showError(msg);

                /* Revert preview on failure */
                if (!profileState.hasExistingPhoto) {
                    $('#avatarCircle').find('img.avatar-image').remove();
                    $('#avatarCircle').removeClass('has-photo');
                    $('#avatarInitials').show();
                    hidePhotoMenu();
                }
                profileState.photoPreview = null;
                $('#photoInput').val('');
            }
        });
    };

    reader.readAsDataURL(file);
}

/* ─── Edit mode ───────────────────────────────────────────────────────── */

function enterEditMode() {
    profileState.isEditing = true;
    setFieldsDisabled(false);
    updateButtonDisplay();
    $('#fullName').focus();
}

function enterLibraryEditMode() {
    profileState.isEditing = true;
    setLibraryFieldsDisabled(false);
    updateLibraryButtonDisplay();
    $('#libraryName').focus();
}

function cancelLibraryEdit() {
    if (profileState.hasChanges) {
        if (!confirm('You have unsaved changes. Are you sure you want to discard them?')) return;
    }

    profileState.isEditing  = false;
    profileState.hasChanges = false;

    $('#libraryName').val(profileState.originalData.libraryName);

    profileState.currentData = JSON.parse(JSON.stringify(profileState.originalData));
    setLibraryFieldsDisabled(true);
    updateLibraryButtonDisplay();
}

function setLibraryFieldsDisabled(disabled) {
    ['#libraryName'].forEach(sel => {
        $(sel).prop('readonly', disabled);
    });
}

function updateLibraryButtonDisplay() {
    if (profileState.isEditing) {
        $('#editLibraryBtn').hide();
        $('#libraryActions').show();
    } else {
        $('#editLibraryBtn').show();
        $('#libraryActions').hide();
    }
}

function validateLibraryForm() {
    const libraryName = $.trim($('#libraryName').val());

    if (!libraryName)              { showError('Library name is required.');                           return false; }
    if (libraryName.length < 3)   { showError('Library name must be at least 3 characters long.');    return false; }

    return true;
}

function saveLibraryInfo() {
    if (!validateLibraryForm()) return;

    showLoading();

    const data = {
        library_name: $.trim($('#libraryName').val())
    };

    $.ajax({
        url: '/update-library/',
        type: 'POST',
        data: data,
        timeout: 30000,
        success: function(response) {
            hideLoading();
            profileState.originalData.libraryName = data.library_name;
            profileState.currentData.libraryName = data.library_name;
            profileState.isEditing = false;
            profileState.hasChanges = false;
            setLibraryFieldsDisabled(true);
            updateLibraryButtonDisplay();
            showSuccess('Library information updated successfully.');
        },
        error: function(xhr) {
            hideLoading();
            let msg = 'Failed to update library information. Please try again.';
            if (xhr.responseJSON && xhr.responseJSON.message) msg = xhr.responseJSON.message;
            showError(msg);
        }
    });
}

function cancelEdit() {
    if (profileState.hasChanges) {
        if (!confirm('You have unsaved changes. Are you sure you want to discard them?')) return;
    }

    profileState.isEditing  = false;
    profileState.hasChanges = false;

    $('#fullName').val(profileState.originalData.fullName);
    $('#emailAddress').val(profileState.originalData.email);
    $('#phoneNumber').val(profileState.originalData.phone);
    $('#dateOfBirth').val(profileState.originalData.dob);
    $('#address').val(profileState.originalData.address);

    profileState.currentData = JSON.parse(JSON.stringify(profileState.originalData));
    setFieldsDisabled(true);
    updateButtonDisplay();
}

function setFieldsDisabled(disabled) {
    ['#fullName', '#emailAddress', '#phoneNumber', '#dateOfBirth', '#address'].forEach(sel => {
        $(sel).prop('readonly', disabled);
    });
}

function updateCurrentData() {
    profileState.currentData = {
        fullName: $.trim($('#fullName').val()),
        email:    $.trim($('#emailAddress').val()),
        phone:    $.trim($('#phoneNumber').val()),
        dob:      $.trim($('#dateOfBirth').val()),
        address:  $.trim($('#address').val())
    };
}

function detectChanges() {
    profileState.hasChanges = !isDataEqual(profileState.currentData, profileState.originalData);
}

function isDataEqual(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
}

function updateButtonDisplay() {
    if (profileState.isEditing) {
        $('#editPersonalBtn').hide();
        $('#personalActions').show();
    } else {
        $('#editPersonalBtn').show();
        $('#personalActions').hide();
    }
}

function updateButtonState() {
    const $btn = $('#savePersonalBtn');
    const ok   = profileState.isEditing && profileState.hasChanges;
    $btn.prop('disabled', !ok).css({ opacity: ok ? '1' : '0.5', cursor: ok ? 'pointer' : 'not-allowed' });
}

/* ─── Validation ──────────────────────────────────────────────────────── */

function validatePersonalForm() {
    const fullName = $.trim($('#fullName').val());
    const email    = $.trim($('#emailAddress').val());
    const phone    = $.trim($('#phoneNumber').val());
    const dob      = $.trim($('#dateOfBirth').val());

    if (!fullName)              { showError('Full name is required.');                           return false; }
    if (fullName.length < 3)   { showError('Full name must be at least 3 characters long.');    return false; }
    if (!email)                 { showError('Email address is required.');                       return false; }
    if (!isValidEmail(email))   { showError('Please enter a valid email address.');              return false; }
    if (phone && !isValidPhone(phone)) { showError('Please enter a valid phone number (10-15 digits).'); return false; }

    if (dob) {
        if (!isValidDate(dob))             { showError('Invalid date of birth.');                       return false; }
        const dobDate = new Date(dob);
        const today   = new Date();
        if (dobDate > today)               { showError('Date of birth cannot be in the future.');        return false; }
        if (today.getFullYear() - dobDate.getFullYear() < 13) { showError('You must be at least 13 years old.'); return false; }
    }

    return true;
}

function isValidEmail(email)      { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email); }
function isValidPhone(phone)      { return /^\d{10,15}$/.test(phone.replace(/\D/g, '')); }
function isValidDate(dateString)  { const d = new Date(dateString); return d instanceof Date && !isNaN(d); }

/* ─── Save profile ────────────────────────────────────────────────────── */

function savePersonalInfo() {
    if (!validatePersonalForm()) return;

    showLoading();

    const parts     = $.trim($('#fullName').val()).split(' ');
    const firstName = parts[0] || '';
    const lastName  = parts.slice(1).join(' ') || '';

    const data = {
        first_name:    firstName,
        last_name:     lastName,
        email:         $.trim($('#emailAddress').val()),
        phone:         $.trim($('#phoneNumber').val()),
        date_of_birth: $.trim($('#dateOfBirth').val()),
        address:       $.trim($('#address').val())
    };

    $.ajax({
        url:     '/update-profile/',
        type:    'POST',
        data:    data,
        timeout: 30000,
        success: function() {
            hideLoading();

            profileState.originalData = {
                fullName: $('#fullName').val(),
                email:    data.email,
                phone:    data.phone,
                dob:      data.date_of_birth,
                address:  data.address
            };
            profileState.currentData  = JSON.parse(JSON.stringify(profileState.originalData));
            profileState.isEditing    = false;
            profileState.hasChanges   = false;

            setFieldsDisabled(true);
            updateButtonDisplay();
            updateButtonState();
            displayAvatarInitials();
            showSuccess('Profile information updated successfully!');
        },
        error: function(xhr) {
            hideLoading();
            let msg = 'Failed to update profile. Please try again.';
            if      (xhr.status === 404)             msg = 'Update endpoint not found. Please contact support.';
            else if (xhr.status === 403)             msg = 'Permission denied. Please log in again.';
            else if (xhr.responseJSON?.message)      msg = xhr.responseJSON.message;
            showError(msg);
        }
    });
}

/* ─── UI helpers ──────────────────────────────────────────────────────── */

function showPasswordChangeModal() { alert('Password change feature coming soon!'); }

function showSuccess(message) {
    $('#successMessage').text(message);
    $('#successAlert').stop(true, true).show().addClass('show');
    setTimeout(() => $('#successAlert').fadeOut(() => $('#successAlert').removeClass('show')), 5000);
}

function showError(message) {
    $('#errorMessage').text(message);
    $('#errorAlert').stop(true, true).show().addClass('show');
    setTimeout(() => $('#errorAlert').fadeOut(() => $('#errorAlert').removeClass('show')), 5000);
    $('html, body').animate({ scrollTop: 0 }, 'smooth');
}

function showLoading() { $('#loadingSpinner').show(); }
function hideLoading() { $('#loadingSpinner').fadeOut(); }

function getCookie(name) {
    if (!document.cookie) return '';
    const match = document.cookie.split(';')
        .map(c => c.trim())
        .find(c => c.startsWith(name + '='));
    return match ? decodeURIComponent(match.substring(name.length + 1)) : '';
}

/* ─── Global keyboard / unload ────────────────────────────────────────── */

$(document).on('keydown', function(e) {
    if (e.key === 'Escape' && profileState.isEditing) cancelEdit();
    if (e.key === 'Escape') closePhotoMenu();
});

$(window).on('beforeunload', function() {
    if (profileState.isEditing && profileState.hasChanges) {
        return 'You have unsaved changes. Are you sure you want to leave?';
    }
});